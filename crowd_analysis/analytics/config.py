
#Centralized configuration for the Crowd Analytics Engine.

from dataclasses import dataclass, field
from typing import Tuple, List


@dataclass(frozen=True)
class TrackerConfig:

    max_match_distance: float = 120.0
    max_disappeared_frames: int = 15

    min_iou_for_match: float = 0.0

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
    history_length: int = 30

    instantaneous_window: int = 1
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

    name: str
    p1: Tuple[float, float]
    p2: Tuple[float, float]
    direction_in: str = "left_to_right"  

@dataclass(frozen=True)
class EntryExitConfig:
    lines: Tuple[EntryExitLine, ...] = field(default_factory=tuple)

    hysteresis_distance_px: float = 8.0


@dataclass(frozen=True)
class FlowConfig:
    min_moving_tracks: int = 3
    uniform_std_deg: float = 25.0
    chaotic_std_deg: float = 70.0


@dataclass(frozen=True)
class AnalyticsBufferConfig:
    buffer_length: int = 60

@dataclass(frozen=True)
class CrowdMetricsConfig:
    growth_window_frames: int = 10


@dataclass(frozen=True)
class EngineConfig:

    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    trajectory: TrajectoryConfig = field(default_factory=TrajectoryConfig)
    density: DensityConfig = field(default_factory=DensityConfig)
    entry_exit: EntryExitConfig = field(default_factory=EntryExitConfig)
    flow: FlowConfig = field(default_factory=FlowConfig)
    buffer: AnalyticsBufferConfig = field(default_factory=AnalyticsBufferConfig)
    crowd_metrics: CrowdMetricsConfig = field(default_factory=CrowdMetricsConfig)
