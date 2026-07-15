"""
conftest.py
-----------
Shared fixtures and synthetic-data generators for the SentinelX
Crowd Intelligence Engine test suite.

Generators here build plain dicts matching the documented input
schema (frame/timestamp/camera_id/image_size/detections), so tests
exercise the real `process_frame()` JSON boundary rather than poking
at internals -- catching schema regressions, not just logic bugs.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from analytics import AnalyticsEngine, EngineConfig
from analytics.config import (
    TrackerConfig,
    TrajectoryConfig,
    DensityConfig,
    EntryExitConfig,
    EntryExitLine,
    FlowConfig,
    AnalyticsBufferConfig,
    CrowdMetricsConfig,
)


def make_bbox(cx: float, cy: float, w: float = 60.0, h: float = 160.0):
    """Axis-aligned bbox centered at (cx, cy)."""
    return [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]


def make_payload(frame, timestamp, detections, width=1920, height=1080, camera_id="cam01"):
    return {
        "frame": frame,
        "timestamp": timestamp,
        "camera_id": camera_id,
        "image_size": {"width": width, "height": height},
        "detections": detections,
    }


def make_detection(cx, cy, w=60.0, h=160.0, confidence=0.9):
    return {"bbox": make_bbox(cx, cy, w, h), "confidence": confidence}


class LinearWalker:
    """A synthetic person moving in a straight line at constant speed."""

    def __init__(self, x0, y0, vx=0.0, vy=0.0):
        self.x = x0
        self.y = y0
        self.vx = vx
        self.vy = vy

    def step(self):
        self.x += self.vx
        self.y += self.vy
        return self.x, self.y


def generate_linear_stream(
    people, num_frames, fps=30.0, width=1920, height=1080, start_ts=1000.0
):
    """
    Generate a list of frame payloads for a set of LinearWalker people
    moving at constant velocity across `num_frames` frames at `fps`.
    Detections outside [-50, width+50] x [-50, height+50] are dropped,
    simulating people leaving the camera's field of view.
    """
    dt = 1.0 / fps
    frames = []
    for f in range(num_frames):
        detections = []
        for p in people:
            x, y = p.step()
            if -50 <= x <= width + 50 and -50 <= y <= height + 50:
                detections.append(make_detection(x, y))
        frames.append(make_payload(f, start_ts + f * dt, detections, width, height))
    return frames


@pytest.fixture
def default_engine():
    return AnalyticsEngine(EngineConfig())


@pytest.fixture
def engine_factory():
    """Factory fixture so tests can build engines with custom configs."""

    def _make(**overrides):
        return AnalyticsEngine(EngineConfig(**overrides))

    return _make
