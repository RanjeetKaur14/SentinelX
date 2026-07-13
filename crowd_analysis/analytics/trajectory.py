import math
from collections import deque
from typing import Dict, Deque, List, Tuple

from .config import TrajectoryConfig
from .models import Track, Point


_DIRECTION_COMPASS: List[str] = [
    "East", "North-East", "North", "North-West",
    "West", "South-West", "South", "South-East",
]

TimedPoint = Tuple[float, Point]


class TrajectoryManager:
    def __init__(self, config: TrajectoryConfig):
        self._config = config
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

        stale_ids = set(self._buffers.keys()) - active_ids
        for tid in stale_ids:
            del self._buffers[tid]

    def _update_single(self, track: Track, timestamp: float) -> None:
        buf = self._buffers.setdefault(
            track.track_id, deque(maxlen=self._config.history_length)
        )

        if track.disappeared == 0:
            buf.append((timestamp, track.centroid))

        track.history = list(buf)

        speed, direction, computed = self._compute_speed_and_direction(buf)
        if computed:
            track.instantaneous_speed = speed
            track.direction = direction
        # else: timestamps didn't advance 
        track.average_speed = self._compute_average_speed(buf)

    def _compute_speed_and_direction(self, buf: Deque[TimedPoint]):
        window = self._config.instantaneous_window
        if len(buf) <= window:
            return 0.0, "Stationary", False

        t_prev, p_prev = buf[-1 - window]
        t_curr, p_curr = buf[-1]
        dt = t_curr - t_prev
        if dt <= 0:
            return 0.0, "Stationary", False

        dx = p_curr[0] - p_prev[0]
        dy = p_curr[1] - p_prev[1]
        distance = math.hypot(dx, dy)
        speed = distance / dt  

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
        angle_deg = math.degrees(math.atan2(-dy, dx))  
        angle_deg = angle_deg % 360
        index = int(((angle_deg + 22.5) % 360) // 45)
        return _DIRECTION_COMPASS[index]
