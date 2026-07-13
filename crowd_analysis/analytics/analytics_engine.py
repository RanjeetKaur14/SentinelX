"""
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

        self._buffer: Deque[FrameAnalytics] = deque(
            maxlen=self._config.buffer.buffer_length
        )

        self._buffer_people_counts: Deque[int] = deque(
            maxlen=self._config.buffer.buffer_length
        )
        self._buffer_heatmaps: Deque[List[List[int]]] = deque(
            maxlen=self._config.buffer.buffer_length
        )

    def process_frame(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        frame_input = FrameInput.from_dict(payload)
        return self.process(frame_input).to_dict()

    def process(self, frame_input: FrameInput) -> FrameAnalytics:
        active_tracks: List[Track] = self._tracker.update(frame_input.detections)
        self._trajectory.update(active_tracks, frame_input.timestamp)

        zone_density, normalized_zone_density, instantaneous_grid = (
            self._density_grid.compute(
                active_tracks, frame_input.image_width, frame_input.image_height
            )
        )
        self._rolling_heatmap.update(instantaneous_grid)
        heatmap_trend = self._rolling_heatmap.trend()

        self._entry_exit.update(active_tracks)
        entry_exit_snapshot = self._entry_exit.snapshot()

        flow_result = self._flow.classify(active_tracks)
        visible_tracks = [t for t in active_tracks if t.disappeared == 0]

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
    
        return self._rolling_heatmap.slow_heatmap()

    @property
    def analytics_buffer(self) -> List[FrameAnalytics]:
        return list(self._buffer)

    @property
    def active_track_count(self) -> int:
        return len(self._tracker.tracks)
