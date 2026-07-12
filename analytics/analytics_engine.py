"""
analytics_engine.py
--------------------
Public entry point for the Crowd Analytics Engine.

`AnalyticsEngine.process_frame()` is the single method the rest of
the SentinelX pipeline (detection upstream, risk-prediction & dashboard
downstream) needs to call. It wires together the tracker, trajectory
manager, density grid, rolling heatmap, entry/exit counter, flow
classifier, and (new in v2) the crowd-metrics aggregator -- each of
which is independently testable and independently swappable (SOLID:
single-responsibility + dependency-friendly design).

Pipeline (v2):

    Tracker -> Trajectory -> Density -> Heatmap -> Flow -> Crowd Metrics -> Output

v1 -> v2 output shape change: the flat `people_count` / `density` /
`heatmap` / `flow` fields have moved into a nested `crowd_metrics`
block (see models.CrowdMetrics), and `flow` is now a structured object
instead of a bare string. This is a deliberate, requested breaking
change to the JSON contract -- see migration notes for the exact
before/after shape.
"""

from collections import deque
from typing import Deque, Dict, Any, List

from .config import EngineConfig
from .models import FrameInput, FrameAnalytics, Track, TrackUpdate, CrowdMetrics
from .tracker import CentroidTracker
from .trajectory import TrajectoryManager
from .density import DensityGrid
from .heatmap import RollingHeatmap
from .entry_exit import EntryExitCounter
from .flow import FlowClassifier
from .crowd_metrics import CrowdMetricsCalculator


class AnalyticsEngine:
    """
    Stateful, single-camera crowd analytics pipeline.

    One instance should be created per camera stream (state such as
    track IDs, entry/exit counts, and the rolling heatmap is specific
    to a single camera's continuous feed).
    """

    def __init__(self, config: EngineConfig = None):
        self._config = config or EngineConfig()

        self._tracker = CentroidTracker(self._config.tracker)
        self._trajectory = TrajectoryManager(self._config.trajectory)
        self._density_grid = DensityGrid(self._config.density)
        self._rolling_heatmap = RollingHeatmap(
            rows=self._config.density.grid_rows,
            cols=self._config.density.grid_cols,
        )
        self._entry_exit = EntryExitCounter(self._config.entry_exit)
        self._flow = FlowClassifier(self._config.flow)
        self._crowd_metrics = CrowdMetricsCalculator(self._config.crowd_metrics)

        # Rolling buffer of past frame-level analytics snapshots
        # (requirement #11: "Analytics Buffer").
        self._buffer: Deque[FrameAnalytics] = deque(
            maxlen=self._config.buffer.buffer_length
        )

        # Lightweight parallel buffers of just the values crowd_metrics
        # needs for growth-rate calculations. Kept separate from
        # `_buffer` (which stores full FrameAnalytics objects) so
        # crowd_metrics.py doesn't need to reach into nested dataclass
        # structure -- it just gets plain lists of numbers/grids.
        self._buffer_people_counts: Deque[int] = deque(
            maxlen=self._config.buffer.buffer_length
        )
        self._buffer_heatmaps: Deque[List[List[int]]] = deque(
            maxlen=self._config.buffer.buffer_length
        )

    def process_frame(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process one raw frame payload (as described in the input spec)
        and return the corresponding analytics JSON dict.
        """
        frame_input = FrameInput.from_dict(payload)
        return self.process(frame_input).to_dict()

    def process(self, frame_input: FrameInput) -> FrameAnalytics:
        """Same as `process_frame` but works with/returns typed objects."""

        # 1-2. Tracking + centroid assignment (tracker computes centroids
        # internally from bboxes; matching now uses combined distance
        # + IoU cost over predicted centroids -- see tracker.py).
        active_tracks: List[Track] = self._tracker.update(frame_input.detections)

        # 3-5. Trajectory history, velocity, direction. Speed is now
        # pixels/second, driven by the frame timestamp.
        self._trajectory.update(active_tracks, frame_input.timestamp)

        # 6-7. Density grid (raw + normalized) + heatmap (single pass,
        # shared computation).
        zone_density, normalized_zone_density, instantaneous_grid = (
            self._density_grid.compute(
                active_tracks, frame_input.image_width, frame_input.image_height
            )
        )
        self._rolling_heatmap.update(instantaneous_grid)
        heatmap_trend = self._rolling_heatmap.trend()

        # 9. Entry/exit counting (hysteresis-gated, per-line breakdown).
        self._entry_exit.update(active_tracks)
        entry_exit_snapshot = self._entry_exit.snapshot()

        # 10. Dominant flow classification (now a structured result:
        # label + confidence + dominant heading + directional entropy).
        flow_result = self._flow.classify(active_tracks)

        # Only report tracks that were actually detected this frame
        # (exclude ones coasting through their "disappeared" grace
        # period) so `people_count` reflects visible people, not
        # tracker memory.
        visible_tracks = [t for t in active_tracks if t.disappeared == 0]

        # 11. Crowd Metrics -- derived, frame-level statistics computed
        # from everything above plus the rolling buffer. No risk
        # scoring happens here; that's the downstream Risk Prediction
        # Engine's job.
        crowd_metrics: CrowdMetrics = self._crowd_metrics.compute(
            tracks=visible_tracks,
            density=zone_density,
            normalized_density=normalized_zone_density,
            instantaneous_heatmap=instantaneous_grid,
            fast_heatmap=self._rolling_heatmap.fast_heatmap(),
            slow_heatmap=self._rolling_heatmap.slow_heatmap(),
            heatmap_trend=heatmap_trend,
            flow=flow_result,
            entry_exit_snapshot=entry_exit_snapshot,
            buffer_people_counts=list(self._buffer_people_counts),
            buffer_heatmaps=list(self._buffer_heatmaps),
        )

        track_updates = [
            TrackUpdate(
                track_id=t.track_id,
                centroid=t.centroid,
                speed=t.instantaneous_speed,
                direction=t.direction,
            )
            for t in visible_tracks
        ]

        result = FrameAnalytics(
            frame=frame_input.frame,
            tracks=track_updates,
            crowd_metrics=crowd_metrics,
        )

        self._buffer.append(result)
        self._buffer_people_counts.append(len(visible_tracks))
        self._buffer_heatmaps.append(instantaneous_grid)

        return result

    @property
    def rolling_heatmap(self) -> List[List[float]]:
        """Slow (baseline) decayed occupancy grid."""
        return self._rolling_heatmap.slow_heatmap()

    @property
    def analytics_buffer(self) -> List[FrameAnalytics]:
        """Rolling history of past frame analytics (requirement #11)."""
        return list(self._buffer)

    @property
    def active_track_count(self) -> int:
        return len(self._tracker.tracks)
