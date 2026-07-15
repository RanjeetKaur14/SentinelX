"""
crowd_metrics.py
-----------------
Computes derived, frame-level crowd metrics from the outputs of the
other analytics modules (Trajectory, Density, Flow, Heatmap, EntryExit,
and the rolling analytics buffer).

IMPORTANT: this module ONLY computes metrics. It does NOT implement
any risk scoring, thresholding-into-alerts, or stampede prediction --
that is explicitly the downstream Risk Prediction Engine's job. This
module's contract is "describe the crowd state and its recent trend
as plain numbers", nothing more. Concretely, this means it deliberately
does NOT compute congestion index, density gradient, reverse-flow
percentage, or stationary-cluster detection -- those require a
judgment call about what the raw numbers *mean* (e.g. "how close is
too close", "what counts as opposing flow"), which belongs exclusively
to the Risk Prediction Engine. This module instead exposes the raw
ingredients those judgments would need: normalized density, a full
direction histogram, and a plain list of stationary track IDs.

Every metric here is a cheap composition of data the rest of the
pipeline already computes -- no new detection, no new tracking, no ML.
That's a deliberate design choice for edge hardware: the "intelligence"
here is in choosing which cheap statistics are actually predictive of
stampede risk, not in computational sophistication.
"""

from typing import Dict, List, Optional, Tuple

from .config import CrowdMetricsConfig
from .models import Track, FlowResult, CrowdMetrics, EntryExitStats, HeatmapBundle


class CrowdMetricsCalculator:
    """Stateless aggregator -- recomputes from current-frame inputs + buffer each call."""

    def __init__(self, config: CrowdMetricsConfig):
        self._config = config

    def compute(
        self,
        tracks: List[Track],
        density: Dict[str, int],
        normalized_density: Dict[str, float],
        instantaneous_heatmap: List[List[int]],
        fast_heatmap: List[List[float]],
        slow_heatmap: List[List[float]],
        heatmap_trend: List[List[float]],
        flow: FlowResult,
        entry_exit_snapshot: Dict[str, object],
        buffer_people_counts: List[int],
        buffer_heatmaps: List[List[List[int]]],
    ) -> CrowdMetrics:
        """
        Args:
            tracks: currently visible tracks (this frame).
            density, normalized_density: this frame's grid outputs
                from DensityGrid.compute().
            instantaneous_heatmap: this frame's raw per-cell counts
                (same data as `density`, matrix form) -- used only
                internally for the zone_growth delta calculation, not
                exposed directly in the output.
            fast_heatmap, slow_heatmap, heatmap_trend: this frame's
                dual-decay grids from RollingHeatmap.
            flow: this frame's FlowResult from FlowClassifier.classify().
            entry_exit_snapshot: EntryExitCounter.snapshot() output.
            buffer_people_counts: people_count history from the analytics
                buffer, oldest-first, used for occupancy_growth.
            buffer_heatmaps: raw heatmap-grid history from the analytics
                buffer, oldest-first, used for zone_growth.
        """
        people_count = len(tracks)

        average_speed = self._average_speed(tracks)
        occupancy_growth = self._occupancy_growth(people_count, buffer_people_counts)
        zone_growth = self._zone_growth(instantaneous_heatmap, buffer_heatmaps)
        stationary_tracks = self._stationary_tracks(tracks)

        entry_exit_stats = EntryExitStats(
            total_entry=int(entry_exit_snapshot.get("entry_count", 0)),
            total_exit=int(entry_exit_snapshot.get("exit_count", 0)),
            per_line=dict(entry_exit_snapshot.get("per_line", {})),
        )
        heatmap_bundle = HeatmapBundle(
            fast=fast_heatmap, slow=slow_heatmap, trend=heatmap_trend
        )

        return CrowdMetrics(
            people_count=people_count,
            average_speed=average_speed,
            occupancy_growth=occupancy_growth,
            zone_growth=zone_growth,
            density=density,
            normalized_density=normalized_density,
            flow=flow,
            stationary_tracks=stationary_tracks,
            entry_exit=entry_exit_stats,
            heatmap=heatmap_bundle,
        )

    # ------------------------------------------------------------------
    # Individual metric computations. Kept as small, independently
    # testable methods rather than one large function.
    # ------------------------------------------------------------------

    @staticmethod
    def _average_speed(tracks: List[Track]) -> float:
        """Mean instantaneous speed (pixels/second) over active tracks."""
        if not tracks:
            return 0.0
        return sum(t.instantaneous_speed for t in tracks) / len(tracks)

    def _occupancy_growth(
        self, current_count: int, buffer_people_counts: List[int]
    ) -> float:
        """
        People-count delta over the configured growth window, using
        the analytics buffer. Positive = crowd growing, negative =
        crowd thinning. This is the single highest-value "is something
        changing right now" signal for stampede early warning -- a
        sudden surge shows up here before density alone would flag it.
        """
        window = self._config.growth_window_frames
        if not buffer_people_counts:
            return 0.0
        reference_idx = max(0, len(buffer_people_counts) - window)
        reference_count = buffer_people_counts[reference_idx]
        return float(current_count - reference_count)

    def _zone_growth(
        self,
        current_heatmap: List[List[int]],
        buffer_heatmaps: List[List[List[int]]],
    ) -> List[List[float]]:
        """
        Per-cell density delta over the growth window -- same idea as
        occupancy_growth but localized per zone, so a bottleneck
        forming in one corner of the frame is visible even if the
        overall crowd size is roughly stable.
        """
        rows = len(current_heatmap)
        cols = len(current_heatmap[0]) if rows else 0

        if not buffer_heatmaps:
            return [[0.0 for _ in range(cols)] for _ in range(rows)]

        window = self._config.growth_window_frames
        reference_idx = max(0, len(buffer_heatmaps) - window)
        reference_grid = buffer_heatmaps[reference_idx]

        return [
            [
                float(current_heatmap[r][c] - reference_grid[r][c])
                for c in range(cols)
            ]
            for r in range(rows)
        ]

    @staticmethod
    def _stationary_tracks(tracks: List[Track]) -> List[int]:
        """
        Plain list of track IDs currently classified Stationary. This
        is a raw measurement only -- it deliberately does NOT attempt
        to determine whether any of these tracks are spatially close
        together (a "cluster"). Whether a set of stationary people
        constitutes a meaningful cluster -- and whether that's
        dangerous -- is an interpretation, and belongs to the
        downstream Risk Prediction Engine.
        """
        return [t.track_id for t in tracks if t.direction == "Stationary"]
