"""
test_integration.py
--------------------
End-to-end tests through AnalyticsEngine.process_frame(), covering
the full pipeline, JSON schema/serialization, and long-running
stability (the things a unit test on a single module can't catch).
"""

import json
import math

import pytest

from analytics import EngineConfig, EntryExitConfig, EntryExitLine
from analytics.config import TrackerConfig, FlowConfig
from conftest import make_payload, make_detection, LinearWalker, generate_linear_stream


class TestJSONSchema:
    def test_output_is_json_serializable(self, engine_factory):
        engine = engine_factory()
        payload = make_payload(0, 1000.0, [make_detection(100, 200)])
        result = engine.process_frame(payload)
        json.dumps(result)  # raises if anything isn't serializable (e.g. NaN, numpy types)

    def test_top_level_schema(self, engine_factory):
        engine = engine_factory()
        payload = make_payload(0, 1000.0, [make_detection(100, 200)])
        result = engine.process_frame(payload)
        assert set(result.keys()) == {"frame", "tracks", "crowd_metrics"}

    def test_crowd_metrics_schema(self, engine_factory):
        engine = engine_factory()
        payload = make_payload(0, 1000.0, [make_detection(100, 200)])
        result = engine.process_frame(payload)
        cm = result["crowd_metrics"]
        expected_keys = {
            "people_count", "average_speed", "occupancy_growth", "zone_growth",
            "density", "normalized_density", "flow", "stationary_tracks",
            "entry_exit", "heatmap",
        }
        assert set(cm.keys()) == expected_keys

    def test_flow_schema(self, engine_factory):
        engine = engine_factory()
        payload = make_payload(0, 1000.0, [make_detection(100, 200)])
        result = engine.process_frame(payload)
        flow = result["crowd_metrics"]["flow"]
        assert set(flow.keys()) == {"label", "confidence", "dominant_heading", "entropy", "direction_histogram"}

    def test_entry_exit_schema(self, engine_factory):
        engine = engine_factory()
        payload = make_payload(0, 1000.0, [make_detection(100, 200)])
        result = engine.process_frame(payload)
        ee = result["crowd_metrics"]["entry_exit"]
        assert set(ee.keys()) == {"total_entry", "total_exit", "per_line"}

    def test_heatmap_schema(self, engine_factory):
        engine = engine_factory()
        payload = make_payload(0, 1000.0, [make_detection(100, 200)])
        result = engine.process_frame(payload)
        hm = result["crowd_metrics"]["heatmap"]
        assert set(hm.keys()) == {"fast", "slow", "trend"}

    def test_track_schema(self, engine_factory):
        engine = engine_factory()
        payload = make_payload(0, 1000.0, [make_detection(100, 200)])
        result = engine.process_frame(payload)
        track = result["tracks"][0]
        assert set(track.keys()) == {"track_id", "centroid", "speed", "direction"}

    def test_no_nan_or_infinity_in_output(self, engine_factory):
        engine = engine_factory()
        for f in range(10):
            payload = make_payload(f, 1000.0 + f * 0.033, [make_detection(100 + f * 10, 200)])
            result = engine.process_frame(payload)
        raw = json.dumps(result)
        assert "NaN" not in raw
        assert "Infinity" not in raw


class TestNoInterpretedVocabulary:
    """The module boundary should hold end-to-end, not just at the
    dataclass level -- confirm the actual JSON never mentions risk
    concepts anywhere, at any nesting depth."""

    def test_no_risk_vocabulary_anywhere_in_output(self, engine_factory):
        engine = engine_factory()
        payload = make_payload(0, 1000.0, [make_detection(100, 200)])
        result = engine.process_frame(payload)
        raw = json.dumps(result).lower()
        for banned in ["risk", "danger", "stampede", "alert", "warning", "congestion"]:
            assert banned not in raw


class TestLongRunningStability:
    def test_two_thousand_frames_stays_stable(self, engine_factory):
        import random
        random.seed(3)
        engine = engine_factory()
        for f in range(2000):
            n = random.randint(0, 20)
            dets = [
                make_detection(random.uniform(0, 1800), random.uniform(0, 1000))
                for _ in range(n)
            ]
            payload = make_payload(f, 1000.0 + f * 0.033, dets)
            result = engine.process_frame(payload)
        # Bounded state: not thousands of leaked tracks/buffers.
        assert engine.active_track_count < 500
        assert len(engine.analytics_buffer) <= 60

    def test_output_remains_serializable_after_long_run(self, engine_factory):
        import random
        random.seed(5)
        engine = engine_factory()
        for f in range(500):
            dets = [make_detection(random.uniform(0, 1800), random.uniform(0, 1000)) for _ in range(10)]
            payload = make_payload(f, 1000.0 + f * 0.033, dets)
            result = engine.process_frame(payload)
        json.dumps(result)


class TestFullPipelineScenario:
    def test_crowd_entering_and_flowing_uniformly(self, engine_factory):
        engine = engine_factory(
            entry_exit=EntryExitConfig(
                lines=(EntryExitLine(name="gate", p1=(150, 0), p2=(150, 1080)),),
                hysteresis_distance_px=8.0,
            ),
            flow=FlowConfig(min_moving_tracks=2),
        )
        people = [LinearWalker(-100 - i * 20, 200 + i * 100, vx=15) for i in range(5)]
        for payload in generate_linear_stream(people, num_frames=40):
            result = engine.process_frame(payload)

        cm = result["crowd_metrics"]
        assert cm["people_count"] == 5
        assert cm["entry_exit"]["total_entry"] == 5
        assert cm["flow"]["label"] == "Uniform"
        assert cm["flow"]["confidence"] > 0.9

    def test_resolution_change_mid_stream_does_not_crash(self, engine_factory):
        engine = engine_factory()
        p1 = make_payload(0, 1000.0, [make_detection(100, 100)], width=1920, height=1080)
        p2 = make_payload(1, 1000.033, [make_detection(100, 100)], width=640, height=480)
        engine.process_frame(p1)
        result = engine.process_frame(p2)  # should not raise
        assert result["crowd_metrics"]["people_count"] == 1
