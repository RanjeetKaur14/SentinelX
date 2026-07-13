"""
test_crowd_metrics.py
----------------------
Covers CrowdMetricsCalculator: occupancy growth, zone growth,
stationary track listing, and confirms the module boundary (no
congestion/risk/interpreted metrics leak into the output).
"""

import pytest

from analytics.config import CrowdMetricsConfig, FlowConfig
from analytics.crowd_metrics import CrowdMetricsCalculator
from analytics.flow import FlowClassifier
from analytics.models import Track, CrowdMetrics


def make_track(track_id, x, y, direction="East", speed=10.0):
    t = Track(track_id=track_id, bbox=(x - 10, y - 10, x + 10, y + 10), centroid=(x, y))
    t.direction = direction
    t.instantaneous_speed = speed
    return t


def empty_grid(rows=4, cols=4, fill=0.0):
    return [[fill for _ in range(cols)] for _ in range(rows)]


def flat_entry_exit_snapshot():
    return {"entry_count": 3, "exit_count": 1, "per_line": {"L1": {"entry_count": 3, "exit_count": 1}}}


class TestAverageSpeed:
    def test_average_speed_over_tracks(self):
        calc = CrowdMetricsCalculator(CrowdMetricsConfig())
        tracks = [make_track(0, 0, 0, speed=10.0), make_track(1, 0, 0, speed=20.0)]
        flow = FlowClassifier(FlowConfig()).classify(tracks)
        result = calc.compute(
            tracks=tracks,
            density={"zone_1": 2},
            normalized_density={"zone_1": 0.001},
            instantaneous_heatmap=empty_grid(),
            fast_heatmap=empty_grid(),
            slow_heatmap=empty_grid(),
            heatmap_trend=empty_grid(),
            flow=flow,
            entry_exit_snapshot=flat_entry_exit_snapshot(),
            buffer_people_counts=[],
            buffer_heatmaps=[],
        )
        assert result.average_speed == pytest.approx(15.0)

    def test_average_speed_zero_for_empty_tracks(self):
        calc = CrowdMetricsCalculator(CrowdMetricsConfig())
        flow = FlowClassifier(FlowConfig()).classify([])
        result = calc.compute(
            tracks=[], density={}, normalized_density={},
            instantaneous_heatmap=empty_grid(), fast_heatmap=empty_grid(),
            slow_heatmap=empty_grid(), heatmap_trend=empty_grid(),
            flow=flow, entry_exit_snapshot={"entry_count": 0, "exit_count": 0, "per_line": {}},
            buffer_people_counts=[], buffer_heatmaps=[],
        )
        assert result.average_speed == 0.0
        assert result.people_count == 0


class TestOccupancyGrowth:
    def test_growth_reflects_buffer_delta(self):
        calc = CrowdMetricsCalculator(CrowdMetricsConfig(growth_window_frames=5))
        tracks = [make_track(i, i * 10, 0) for i in range(8)]  # current count = 8
        flow = FlowClassifier(FlowConfig()).classify(tracks)
        # Buffer represents the last 5 frames' people counts, oldest first.
        buffer_counts = [2, 3, 3, 4, 4]
        result = calc.compute(
            tracks=tracks, density={}, normalized_density={},
            instantaneous_heatmap=empty_grid(), fast_heatmap=empty_grid(),
            slow_heatmap=empty_grid(), heatmap_trend=empty_grid(),
            flow=flow, entry_exit_snapshot={"entry_count": 0, "exit_count": 0, "per_line": {}},
            buffer_people_counts=buffer_counts, buffer_heatmaps=[],
        )
        # reference is buffer[max(0, len-window)] = buffer[0] = 2
        assert result.occupancy_growth == pytest.approx(6.0)

    def test_growth_zero_when_buffer_empty(self):
        calc = CrowdMetricsCalculator(CrowdMetricsConfig())
        flow = FlowClassifier(FlowConfig()).classify([])
        result = calc.compute(
            tracks=[], density={}, normalized_density={},
            instantaneous_heatmap=empty_grid(), fast_heatmap=empty_grid(),
            slow_heatmap=empty_grid(), heatmap_trend=empty_grid(),
            flow=flow, entry_exit_snapshot={"entry_count": 0, "exit_count": 0, "per_line": {}},
            buffer_people_counts=[], buffer_heatmaps=[],
        )
        assert result.occupancy_growth == 0.0


class TestZoneGrowth:
    def test_zone_growth_per_cell_delta(self):
        calc = CrowdMetricsCalculator(CrowdMetricsConfig(growth_window_frames=2))
        current = [[5, 0], [0, 0]]
        history = [[[1, 0], [0, 0]], [[3, 0], [0, 0]]]  # oldest-first
        flow = FlowClassifier(FlowConfig()).classify([])
        result = calc.compute(
            tracks=[], density={}, normalized_density={},
            instantaneous_heatmap=current, fast_heatmap=current,
            slow_heatmap=current, heatmap_trend=empty_grid(2, 2),
            flow=flow, entry_exit_snapshot={"entry_count": 0, "exit_count": 0, "per_line": {}},
            buffer_people_counts=[], buffer_heatmaps=history,
        )
        # reference_idx = max(0, 2-2) = 0 -> history[0] = [[1,0],[0,0]]
        assert result.zone_growth[0][0] == pytest.approx(4.0)
        assert result.zone_growth[1][1] == pytest.approx(0.0)


class TestStationaryTracks:
    def test_lists_only_stationary_track_ids_no_clustering(self):
        calc = CrowdMetricsCalculator(CrowdMetricsConfig())
        tracks = [
            make_track(0, 0, 0, direction="Stationary"),
            make_track(1, 5, 5, direction="Stationary"),  # close to track 0
            make_track(2, 900, 900, direction="Stationary"),  # far away
            make_track(3, 100, 100, direction="East"),
        ]
        flow = FlowClassifier(FlowConfig()).classify(tracks)
        result = calc.compute(
            tracks=tracks, density={}, normalized_density={},
            instantaneous_heatmap=empty_grid(), fast_heatmap=empty_grid(),
            slow_heatmap=empty_grid(), heatmap_trend=empty_grid(),
            flow=flow, entry_exit_snapshot={"entry_count": 0, "exit_count": 0, "per_line": {}},
            buffer_people_counts=[], buffer_heatmaps=[],
        )
        assert set(result.stationary_tracks) == {0, 1, 2}
        assert 3 not in result.stationary_tracks


class TestEntryExitPassthrough:
    def test_entry_exit_stats_wired_through(self):
        calc = CrowdMetricsCalculator(CrowdMetricsConfig())
        flow = FlowClassifier(FlowConfig()).classify([])
        result = calc.compute(
            tracks=[], density={}, normalized_density={},
            instantaneous_heatmap=empty_grid(), fast_heatmap=empty_grid(),
            slow_heatmap=empty_grid(), heatmap_trend=empty_grid(),
            flow=flow, entry_exit_snapshot=flat_entry_exit_snapshot(),
            buffer_people_counts=[], buffer_heatmaps=[],
        )
        assert result.entry_exit.total_entry == 3
        assert result.entry_exit.total_exit == 1
        assert result.entry_exit.per_line["L1"]["entry_count"] == 3


class TestModuleBoundary:
    """
    Confirms the risk/interpretation boundary: CrowdMetrics should
    never expose congestion index, density gradient, reverse-flow
    percentage, or stationary-cluster counts -- those belong to the
    downstream Risk Prediction Engine.
    """

    def test_no_interpreted_risk_fields_present(self):
        fields = set(CrowdMetrics.__dataclass_fields__.keys())
        forbidden = {
            "congestion_index", "density_gradient",
            "reverse_flow_percentage", "stationary_clusters",
            "risk_score", "alert_level", "danger",
        }
        assert fields.isdisjoint(forbidden)

    def test_to_dict_has_no_forbidden_vocabulary_in_keys(self):
        calc = CrowdMetricsCalculator(CrowdMetricsConfig())
        flow = FlowClassifier(FlowConfig()).classify([])
        result = calc.compute(
            tracks=[], density={}, normalized_density={},
            instantaneous_heatmap=empty_grid(), fast_heatmap=empty_grid(),
            slow_heatmap=empty_grid(), heatmap_trend=empty_grid(),
            flow=flow, entry_exit_snapshot={"entry_count": 0, "exit_count": 0, "per_line": {}},
            buffer_people_counts=[], buffer_heatmaps=[],
        )
        keys = set(result.to_dict().keys())
        forbidden_substrings = ["risk", "danger", "alert", "warning", "congestion"]
        for key in keys:
            for bad in forbidden_substrings:
                assert bad not in key.lower()
