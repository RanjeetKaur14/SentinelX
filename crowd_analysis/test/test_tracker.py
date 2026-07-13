"""
test_tracker.py
----------------
Covers CentroidTracker: track creation, deletion, persistence,
occlusion recovery, crossing paths, and degenerate/malformed
bounding box inputs.
"""

import pytest

from analytics import EngineConfig
from analytics.config import TrackerConfig
from conftest import make_payload, make_detection, LinearWalker, generate_linear_stream


class TestTrackCreation:
    def test_new_detection_spawns_a_track(self, engine_factory):
        engine = engine_factory()
        payload = make_payload(0, 1000.0, [make_detection(100, 200)])
        result = engine.process_frame(payload)
        assert len(result["tracks"]) == 1
        assert result["tracks"][0]["track_id"] == 0

    def test_multiple_detections_spawn_multiple_tracks(self, engine_factory):
        engine = engine_factory()
        dets = [make_detection(x, 200) for x in (100, 500, 900)]
        payload = make_payload(0, 1000.0, dets)
        result = engine.process_frame(payload)
        assert len(result["tracks"]) == 3
        assert {t["track_id"] for t in result["tracks"]} == {0, 1, 2}

    def test_empty_frame_produces_no_tracks(self, engine_factory):
        engine = engine_factory()
        payload = make_payload(0, 1000.0, [])
        result = engine.process_frame(payload)
        assert result["tracks"] == []
        assert result["crowd_metrics"]["people_count"] == 0


class TestTrackPersistence:
    def test_stationary_person_keeps_same_id(self, engine_factory):
        engine = engine_factory()
        for f in range(5):
            payload = make_payload(f, 1000.0 + f * 0.033, [make_detection(500, 500)])
            result = engine.process_frame(payload)
        assert len(result["tracks"]) == 1
        assert result["tracks"][0]["track_id"] == 0

    def test_moving_person_keeps_same_id(self, engine_factory):
        engine = engine_factory()
        walker = LinearWalker(100, 300, vx=10)
        ids_seen = set()
        for payload in generate_linear_stream([walker], num_frames=20):
            result = engine.process_frame(payload)
            ids_seen.update(t["track_id"] for t in result["tracks"])
        assert ids_seen == {0}


class TestOcclusionRecovery:
    def test_recovers_id_after_brief_occlusion(self, engine_factory):
        engine = engine_factory(
            tracker=TrackerConfig(max_disappeared_frames=5, max_match_distance=150)
        )
        x = 100
        ids_seen = []
        for f in range(20):
            x += 10
            dets = [] if 5 <= f <= 8 else [make_detection(x, 300)]
            payload = make_payload(f, 1000.0 + f * 0.033, dets)
            result = engine.process_frame(payload)
            ids_seen.extend(t["track_id"] for t in result["tracks"])
        assert set(ids_seen) == {0}, "track ID should survive a brief occlusion"

    def test_recovers_id_after_occlusion_while_moving_fast(self, engine_factory):
        """
        Regression test for a bug found during QA: constant-velocity
        prediction didn't scale with elapsed disappeared frames, so a
        fast-moving track re-appearing after a multi-frame occlusion
        got assigned a NEW id instead of recovering its old one.
        """
        engine = engine_factory(
            tracker=TrackerConfig(max_disappeared_frames=8, max_match_distance=60)
        )
        x = 100
        speed = 25  # fast mover, px/frame
        ids_seen = []
        for f in range(20):
            x += speed
            dets = [] if 3 <= f <= 8 else [make_detection(x, 300)]
            payload = make_payload(f, 1000.0 + f * 0.033, dets)
            result = engine.process_frame(payload)
            ids_seen.extend(t["track_id"] for t in result["tracks"])
        assert set(ids_seen) == {0}

    def test_new_id_after_occlusion_exceeds_grace_period(self, engine_factory):
        engine = engine_factory(
            tracker=TrackerConfig(max_disappeared_frames=3, max_match_distance=150)
        )
        x = 100
        ids_seen = []
        for f in range(20):
            x += 10
            # 6-frame gap, exceeds the 3-frame grace period
            dets = [] if 3 <= f <= 8 else [make_detection(x, 300)]
            payload = make_payload(f, 1000.0 + f * 0.033, dets)
            result = engine.process_frame(payload)
            ids_seen.extend(t["track_id"] for t in result["tracks"])
        # A NEW id is the expected/documented behavior once the grace
        # period is exceeded -- this should NOT recover the old id.
        assert len(set(ids_seen)) == 2


class TestCrossingPeople:
    def test_two_people_crossing_paths_do_not_crash(self, engine_factory):
        engine = engine_factory()
        left = LinearWalker(100, 300, vx=20)
        right = LinearWalker(900, 300, vx=-20)
        for payload in generate_linear_stream([left, right], num_frames=30):
            engine.process_frame(payload)
        # No strict ID-swap assertion here (greedy matching gives no
        # hard guarantee under a head-on crossing) -- this test only
        # asserts the engine stays stable (no crash, track count sane).
        assert engine.active_track_count <= 2

    def test_dense_opposing_streams_stay_stable(self, engine_factory):
        engine = engine_factory()
        people = [LinearWalker(100 + i * 15, 300, vx=3) for i in range(8)]
        people += [LinearWalker(700 - i * 15, 305, vx=-3) for i in range(8)]
        for payload in generate_linear_stream(people, num_frames=15, width=800, height=600):
            result = engine.process_frame(payload)
        assert engine.active_track_count == 16


class TestDegenerateBoxes:
    @pytest.mark.parametrize(
        "bbox",
        [
            [-100, -50, -40, 50],       # negative coordinates
            [500, 500, 500, 500],       # zero-area box
            [300, 300, 100, 100],       # inverted (x2 < x1, y2 < y1)
            [-99999, -99999, 99999, 99999],  # absurdly large box
            [5000, 5000, 5100, 5300],   # fully outside the frame
        ],
    )
    def test_degenerate_bbox_does_not_crash(self, engine_factory, bbox):
        engine = engine_factory()
        payload = make_payload(
            0, 1000.0, [{"bbox": bbox, "confidence": 0.9}]
        )
        result = engine.process_frame(payload)  # should not raise
        assert result["crowd_metrics"]["people_count"] == 1

    def test_zero_confidence_detection_still_tracked(self, engine_factory):
        engine = engine_factory()
        payload = make_payload(0, 1000.0, [{"bbox": [100, 100, 160, 300], "confidence": 0.0}])
        result = engine.process_frame(payload)
        assert len(result["tracks"]) == 1


class TestConfigValidation:
    """
    Regression tests for a bug found during QA: several config fields
    had no validation and could cause ZeroDivisionError, IndexError,
    or silent NaN propagation deep inside a frame-processing call
    instead of a clear failure at config-construction time.
    """

    def test_zero_max_match_distance_rejected(self):
        with pytest.raises(ValueError):
            TrackerConfig(max_match_distance=0)

    def test_negative_max_match_distance_rejected(self):
        with pytest.raises(ValueError):
            TrackerConfig(max_match_distance=-10)

    def test_default_config_still_constructs(self):
        # Guard against the validation itself being too strict.
        EngineConfig()
