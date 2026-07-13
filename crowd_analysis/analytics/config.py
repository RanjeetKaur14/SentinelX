"""
config.py
---------
Centralized configuration for the Crowd Analytics Engine.

Every tunable parameter lives here so the rest of the codebase never
hardcodes a "magic number". This makes the engine easy to retune for
different cameras, hardware, or venues without touching logic code.
"""

from dataclasses import dataclass, field
from typing import Tuple, List


@dataclass(frozen=True)
class TrackerConfig:
    """Parameters for the lightweight centroid tracker."""

    # Maximum centroid displacement (pixels) allowed to associate a
    # detection with an existing track in one frame. Prevents far-away
    # detections from being matched to the wrong track.
    max_match_distance: float = 120.0

    # Number of *consecutive* frames a track is allowed to go
    # undetected before it is removed ("disappeared" counter).
    max_disappeared_frames: int = 15

    # Minimum IoU required (in addition to distance) to accept a match.
    # Set to 0 to disable IoU gating and rely on distance only, which
    # is cheaper and usually sufficient for sparse-to-medium crowds.
    min_iou_for_match: float = 0.0

    # Weights for the combined matching cost:
    #   cost = distance_weight * normalized_distance
    #        + iou_weight * (1 - IoU)
    # Distance dominates by default (0.6/0.4 split) since it's the
    # more reliable signal at low crowd density; IoU's contribution
    # grows in relative importance exactly when centroids get close
    # together (dense crowds), which is when it's needed most.
    distance_weight: float = 0.6
    iou_weight: float = 0.4

    def __post_init__(self):
        if self.max_match_distance <= 0:
            raise ValueError(
                "max_match_distance must be > 0 -- it's used as a "
                "divisor when normalizing match cost; 0 or negative "
                "causes silent division-by-zero (NaN/inf) in the "
                "tracker's matching cost, not a clean failure."
            )


@dataclass(frozen=True)
class TrajectoryConfig:
    """Parameters for per-track trajectory history."""

    # Number of past centroids retained per track (ring buffer size).
    history_length: int = 30

    # Number of frames back used to compute *instantaneous* velocity.
    # A value of 1 means "difference between this frame and the last".
    instantaneous_window: int = 1

    # Direction is reported as "Stationary" if the average speed over
    # the instantaneous window is below this threshold (pixels/frame).
    stationary_speed_threshold: float = 1.5

    def __post_init__(self):
        if self.history_length <= 0:
            raise ValueError(
                "history_length must be > 0 -- 0 silently disables "
                "all speed/direction computation (every track reads "
                "as Stationary forever) rather than failing clearly."
            )
        if self.instantaneous_window <= 0:
            raise ValueError("instantaneous_window must be > 0.")


@dataclass(frozen=True)
class DensityConfig:
    """Parameters for grid-based density / heatmap computation."""

    grid_rows: int = 4
    grid_cols: int = 4

    def __post_init__(self):
        if self.grid_rows <= 0 or self.grid_cols <= 0:
            raise ValueError(
                "grid_rows and grid_cols must both be > 0 -- they're "
                "used as divisors when computing cell size in "
                "density.py; 0 causes a hard ZeroDivisionError at the "
                "first frame processed, rather than a clear failure "
                "at config-construction time."
            )


@dataclass(frozen=True)
class EntryExitLine:
    """
    A single virtual counting line defined by two endpoints in image
    coordinates: (x1, y1) -> (x2, y2).

    The line has an implicit "positive" side determined by the sign of
    the cross product used in entry_exit.py. `direction_in` documents,
    for humans, which crossing direction counts as an "entry".
    """

    name: str
    p1: Tuple[float, float]
    p2: Tuple[float, float]
    direction_in: str = "left_to_right"  # documentation only


@dataclass(frozen=True)
class EntryExitConfig:
    """Container for all configured virtual lines."""

    lines: Tuple[EntryExitLine, ...] = field(default_factory=tuple)

    # Minimum perpendicular distance (pixels) a track's centroid must
    # be from a line before its "side" is allowed to update. Without
    # this, a track sitting near-exactly on the line can flicker
    # sign frame-to-frame (normal at 30fps -- people don't move in
    # clean steps) and get double-counted on every wobble. This is a
    # deliberately simple hysteresis band, not a state machine.
    hysteresis_distance_px: float = 8.0


@dataclass(frozen=True)
class FlowConfig:
    """Parameters for dominant crowd-flow classification."""

    # Minimum number of *moving* tracks required before flow is
    # classified at all. Below this, flow is reported as "Uniform"
    # (i.e. no meaningful crowd motion / near-empty scene).
    min_moving_tracks: int = 3

    # Circular standard deviation (in degrees) of movement headings
    # below which flow is considered "Uniform".
    uniform_std_deg: float = 25.0

    # Circular standard deviation (in degrees) above which flow is
    # considered "Chaotic". Between uniform_std_deg and this value,
    # flow is classified as "Mixed".
    chaotic_std_deg: float = 70.0


@dataclass(frozen=True)
class AnalyticsBufferConfig:
    """Parameters for the rolling analytics history buffer."""

    # Number of past frame-level analytics snapshots retained
    # (used for smoothing / short-term trend queries if needed).
    buffer_length: int = 60


@dataclass(frozen=True)
class CrowdMetricsConfig:
    """Parameters for the derived crowd-metrics module (crowd_metrics.py)."""

    # How many past buffered frames back to look when computing
    # occupancy_growth / zone_growth deltas. A small window (e.g. 10
    # frames at ~30fps = ~0.3s) is enough to catch a sudden surge
    # without being so long it smooths the signal away.
    growth_window_frames: int = 10


@dataclass(frozen=True)
class EngineConfig:
    """Top-level configuration bundle passed into AnalyticsEngine."""

    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    trajectory: TrajectoryConfig = field(default_factory=TrajectoryConfig)
    density: DensityConfig = field(default_factory=DensityConfig)
    entry_exit: EntryExitConfig = field(default_factory=EntryExitConfig)
    flow: FlowConfig = field(default_factory=FlowConfig)
    buffer: AnalyticsBufferConfig = field(default_factory=AnalyticsBufferConfig)
    crowd_metrics: CrowdMetricsConfig = field(default_factory=CrowdMetricsConfig)
