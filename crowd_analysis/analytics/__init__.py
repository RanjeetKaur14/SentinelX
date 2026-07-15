"""
Crowd Analytics Engine -- SentinelX

Public API:
    from analytics import AnalyticsEngine, EngineConfig

    engine = AnalyticsEngine(EngineConfig())
    result = engine.process_frame(frame_payload)  # -> dict, JSON-ready
"""

from .analytics_engine import AnalyticsEngine
from .config import (
    EngineConfig,
    TrackerConfig,
    TrajectoryConfig,
    DensityConfig,
    EntryExitConfig,
    EntryExitLine,
    FlowConfig,
    AnalyticsBufferConfig,
    CrowdMetricsConfig,
)
from .models import (
    FrameInput,
    FrameAnalytics,
    Track,
    Detection,
    CrowdMetrics,
    FlowResult,
    EntryExitStats,
    HeatmapBundle,
)

__all__ = [
    "AnalyticsEngine",
    "EngineConfig",
    "TrackerConfig",
    "TrajectoryConfig",
    "DensityConfig",
    "EntryExitConfig",
    "EntryExitLine",
    "FlowConfig",
    "AnalyticsBufferConfig",
    "CrowdMetricsConfig",
    "FrameInput",
    "FrameAnalytics",
    "Track",
    "Detection",
    "CrowdMetrics",
    "FlowResult",
    "EntryExitStats",
    "HeatmapBundle",
]
