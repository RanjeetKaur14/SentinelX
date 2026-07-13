"""
trajectory.py
-------------
Maintains per-track centroid history and derives velocity/direction.

v1 -> v2 change: speed is now computed in pixels/second using frame
timestamps, instead of pixels/frame. Pixels/frame silently assumes a
constant, reliable frame rate -- on edge hardware (Pi 5 / Jetson Nano)
under load, frames get dropped, and a frame-count-based speed metric
would misreport crowd velocity purely due to that variability, which
is a bad failure mode for a safety-relevant signal. Using timestamps
makes speed robust to that.

Kept deliberately simple otherwise: a bounded deque per track (O(1)
append, automatic eviction) and closed-form displacement math. No
filtering (Kalman/EMA) is applied by default to keep CPU cost minimal,
though `average_speed` naturally smooths noise by averaging over the
full history window.
"""

import math
from collections import deque
from typing import Dict, Deque, List, Tuple

from .config import TrajectoryConfig
from .models import Track, Point


_DIRECTION_COMPASS: List[str] = [
    "East", "North-East", "North", "North-West",
    "West", "South-West", "South", "South-East",
]

# A single (timestamp, centroid) sample in a track's history buffer.
TimedPoint = Tuple[float, Point]


class TrajectoryManager:
    """
    Owns a bounded history buffer per track and updates each Track's
    `history`, `instantaneous_speed`, `average_speed`, and `direction`
    fields in place every frame.
    """

    def __init__(self, config: TrajectoryConfig):
        self._config = config
        # Separate deque store keyed by track_id so history survives
        # even though Track.history is kept as a plain list for easy
        # JSON/debug inspection.
        self._buffers: Dict[int, Deque[TimedPoint]] = {}

    def update(self, tracks: List[Track], timestamp: float) -> None:
        """
        Update trajectory analytics for every currently active track.

        Args:
            tracks: active tracks from the tracker this frame.
            timestamp: the current frame's timestamp (seconds, same
                units as FrameInput.timestamp), used to compute
                pixels/second speed.
        """
        active_ids = set()
        for track in tracks:
            active_ids.add(track.track_id)
            self._update_single(track, timestamp)

        # Drop buffers for tracks that no longer exist (already removed
        # from the tracker) to avoid unbounded memory growth over a
        # long-running stream.
        stale_ids = set(self._buffers.keys()) - active_ids
        for tid in stale_ids:
            del self._buffers[tid]

    def _update_single(self, track: Track, timestamp: float) -> None:
        buf = self._buffers.setdefault(
            track.track_id, deque(maxlen=self._config.history_length)
        )

        # Only append a fresh sample when the track was actually matched
        # this frame (disappeared == 0). A track that is coasting
        # through its grace period keeps its last known position.
        if track.disappeared == 0:
            buf.append((timestamp, track.centroid))

        track.history = list(buf)

        speed, direction, computed = self._compute_speed_and_direction(buf)
        if computed:
            track.instantaneous_speed = speed
            track.direction = direction
        # else: timestamps didn't advance (duplicate/out-of-order --
        # a plausible frame-drop/clock-stall scenario on edge hardware
        # under load). Deliberately hold the track's last known
        # speed/direction rather than overwriting it with a false
        # "Stationary" reading -- silently reporting a fast-moving
        # crowd as stationary during exactly the kind of transient
        # glitch a real surge could coincide with is a worse failure
        # mode than briefly reusing a slightly stale value.
        track.average_speed = self._compute_average_speed(buf)

    def _compute_speed_and_direction(self, buf: Deque[TimedPoint]):
        """
        Returns (speed, direction, computed). `computed` is False when
        there wasn't enough history yet, or timestamps didn't advance
        -- in both cases the caller should hold the track's previous
        reading rather than trust the (0.0, "Stationary") placeholder
        returned alongside `computed=False`.
        """
        window = self._config.instantaneous_window
        if len(buf) <= window:
            return 0.0, "Stationary", False

        t_prev, p_prev = buf[-1 - window]
        t_curr, p_curr = buf[-1]
        dt = t_curr - t_prev
        if dt <= 0:
            # Duplicate/out-of-order timestamps -- can't compute a
            # speed at all (not even zero, since we don't know how
            # much time actually passed). Let the caller decide how
            # to handle it instead of asserting "no motion" here.
            return 0.0, "Stationary", False

        dx = p_curr[0] - p_prev[0]
        dy = p_curr[1] - p_prev[1]
        distance = math.hypot(dx, dy)
        speed = distance / dt  # pixels/second

        if speed < self._config.stationary_speed_threshold:
            return speed, "Stationary", True

        direction = self._vector_to_direction(dx, dy)
        return speed, direction, True

    def _compute_average_speed(self, buf: Deque[TimedPoint]) -> float:
        if len(buf) < 2:
            return 0.0
        pts = list(buf)
        total_distance = 0.0
        total_time = 0.0
        for i in range(1, len(pts)):
            t_prev, p_prev = pts[i - 1]
            t_curr, p_curr = pts[i]
            dt = t_curr - t_prev
            if dt <= 0:
                continue
            total_distance += math.hypot(
                p_curr[0] - p_prev[0], p_curr[1] - p_prev[1]
            )
            total_time += dt
        return total_distance / total_time if total_time > 0 else 0.0

    @staticmethod
    def _vector_to_direction(dx: float, dy: float) -> str:
        """
        Map a displacement vector to one of 8 compass directions.

        Image-coordinate convention: +x is East, +y is South (down),
        matching standard OpenCV/pixel coordinates.
        """
        angle_deg = math.degrees(math.atan2(-dy, dx))  # flip y for compass feel
        angle_deg = angle_deg % 360
        index = int(((angle_deg + 22.5) % 360) // 45)
        return _DIRECTION_COMPASS[index]
