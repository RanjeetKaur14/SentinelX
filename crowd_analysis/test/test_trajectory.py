"""
test_trajectory.py
-------------------
Covers TrajectoryManager: direction estimation, speed (pixels/second),
timestamp handling (including stalls), history pruning, and
stationary vs. moving classification.
"""

import math

import pytest

from analytics.config import TrajectoryConfig
from analytics.trajectory import TrajectoryManager
from analytics.models import Track


def fresh_track(track_id=0, x=0.0, y=0.0):
    return Track(track_id=track_id, bbox=(x - 10, y - 10, x + 10, y + 10), centroid=(x, y))


class TestSpeedInPixelsPerSecond:
    def test_speed_matches_distance_over_time(self):
        tm = TrajectoryManager(TrajectoryConfig(history_length=10, instantaneous_window=1))
        t = fresh_track(0, 0, 0)

        tm.update([t], timestamp=0.0)
        t.centroid = (30.0, 0.0)  # 30px displacement
        tm.update([t], timestamp=0.5)  # over 0.5s -> 60 px/s

        assert t.instantaneous_speed == pytest.approx(60.0, abs=1e-6)
        assert t.direction == "East"

    def test_average_speed_over_multiple_segments(self):
        tm = TrajectoryManager(TrajectoryConfig(history_length=10, instantaneous_window=1))
        t = fresh_track(0, 0, 0)
        ts = 0.0
        for step in range(5):
            t.centroid = (t.centroid[0] + 10, 0.0)
            ts += 0.1
            tm.update([t], timestamp=ts)
        # 10px every 0.1s => 100 px/s average, consistently
        assert t.average_speed == pytest.approx(100.0, rel=0.05)


class TestDirectionEstimation:
    @pytest.mark.parametrize(
        "dx,dy,expected",
        [
            (10, 0, "East"),
            (-10, 0, "West"),
            (0, -10, "North"),   # -y is "up"/North in image coords
            (0, 10, "South"),
            (10, -10, "North-East"),
            (-10, -10, "North-West"),
            (10, 10, "South-East"),
            (-10, 10, "South-West"),
        ],
    )
    def test_eight_compass_directions(self, dx, dy, expected):
        tm = TrajectoryManager(TrajectoryConfig(history_length=10, instantaneous_window=1))
        t = fresh_track(0, 100, 100)
        tm.update([t], timestamp=0.0)
        t.centroid = (100 + dx, 100 + dy)
        tm.update([t], timestamp=1.0)
        assert t.direction == expected

    def test_slow_motion_below_threshold_is_stationary(self):
        tm = TrajectoryManager(
            TrajectoryConfig(history_length=10, instantaneous_window=1, stationary_speed_threshold=5.0)
        )
        t = fresh_track(0, 0, 0)
        tm.update([t], timestamp=0.0)
        t.centroid = (1.0, 0.0)  # tiny movement
        tm.update([t], timestamp=1.0)  # 1 px/s, below threshold
        assert t.direction == "Stationary"


class TestTimestampHandling:
    def test_duplicate_timestamp_holds_last_known_reading(self):
        """
        Regression test for a bug found during QA: a stalled/duplicate
        timestamp (frame-drop / clock-glitch scenario) used to reset
        speed and direction to (0.0, "Stationary") even when the track
        was genuinely moving fast -- a dangerous silent misclassification
        for a stampede-detection system. It should now hold the last
        known valid reading instead.
        """
        tm = TrajectoryManager(TrajectoryConfig(history_length=10, instantaneous_window=1))
        t = fresh_track(0, 0, 0)
        tm.update([t], timestamp=0.0)
        t.centroid = (30.0, 0.0)
        tm.update([t], timestamp=0.5)  # 60 px/s East -- established
        assert t.instantaneous_speed == pytest.approx(60.0, abs=1e-6)

        t.centroid = (60.0, 0.0)
        tm.update([t], timestamp=0.5)  # STALLED timestamp (duplicate)
        assert t.instantaneous_speed == pytest.approx(60.0, abs=1e-6), (
            "speed should hold its last known value during a timestamp "
            "stall, not reset to 0.0"
        )
        assert t.direction == "East"

    def test_first_frame_has_zero_speed_not_a_crash(self):
        tm = TrajectoryManager(TrajectoryConfig())
        t = fresh_track(0, 0, 0)
        tm.update([t], timestamp=0.0)
        assert t.instantaneous_speed == 0.0
        assert t.direction == "Stationary"


class TestHistoryPruning:
    def test_history_bounded_by_history_length(self):
        tm = TrajectoryManager(TrajectoryConfig(history_length=5, instantaneous_window=1))
        t = fresh_track(0, 0, 0)
        for i in range(50):
            t.centroid = (float(i), 0.0)
            tm.update([t], timestamp=float(i) * 0.1)
        assert len(t.history) == 5

    def test_long_running_trajectory_does_not_leak_memory(self):
        tm = TrajectoryManager(TrajectoryConfig(history_length=30, instantaneous_window=1))
        t = fresh_track(0, 0, 0)
        for i in range(20000):
            t.centroid = (float(i % 500), 0.0)
            tm.update([t], timestamp=float(i) * 0.033)
        assert len(t.history) == 30  # bounded regardless of frame count
        assert len(tm._buffers) == 1  # only this one track's buffer retained

    def test_stale_track_buffer_is_dropped(self):
        tm = TrajectoryManager(TrajectoryConfig())
        t1 = fresh_track(0, 0, 0)
        t2 = fresh_track(1, 100, 100)
        tm.update([t1, t2], timestamp=0.0)
        assert len(tm._buffers) == 2
        tm.update([t1], timestamp=0.1)  # t2 no longer active
        assert len(tm._buffers) == 1


class TestZeroInstantaneousWindow:
    def test_instantaneous_window_must_be_positive(self):
        with pytest.raises(ValueError):
            TrajectoryConfig(instantaneous_window=0)

    def test_history_length_must_be_positive(self):
        with pytest.raises(ValueError):
            TrajectoryConfig(history_length=0)
