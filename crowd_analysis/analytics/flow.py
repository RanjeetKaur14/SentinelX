import math
from collections import Counter
from typing import List, Optional, Dict

from .config import FlowConfig
from .models import Track, FlowResult


_DIRECTION_TO_ANGLE_DEG = {
    "East": 0, "North-East": 45, "North": 90, "North-West": 135,
    "West": 180, "South-West": 225, "South": 270, "South-East": 315,
}
_COMPASS_BINS = list(_DIRECTION_TO_ANGLE_DEG.keys())
_ALL_DIRECTIONS = _COMPASS_BINS + ["Stationary"]


class FlowClassifier:
    def __init__(self, config: FlowConfig):
        self._config = config

    def classify(self, tracks: List[Track]) -> FlowResult:
        moving = [t for t in tracks if t.direction != "Stationary"]
        histogram = self._direction_histogram(tracks)

        if len(moving) < self._config.min_moving_tracks:
            return FlowResult(
                label="Uniform",
                confidence=0.0,
                dominant_heading=None,
                entropy=0.0,
                direction_histogram=histogram,
            )

        sin_sum = 0.0
        cos_sum = 0.0
        for track in moving:
            angle_deg = _DIRECTION_TO_ANGLE_DEG.get(track.direction, 0)
            angle_rad = math.radians(angle_deg)
            sin_sum += math.sin(angle_rad)
            cos_sum += math.cos(angle_rad)

        n = len(moving)
        mean_sin = sin_sum / n
        mean_cos = cos_sum / n
        mean_resultant_length = math.hypot(mean_sin, mean_cos)
        clamped_r = min(max(mean_resultant_length, 1e-9), 1.0)
        circ_std_rad = math.sqrt(-2.0 * math.log(clamped_r))
        circ_std_deg = math.degrees(circ_std_rad)

        if circ_std_deg <= self._config.uniform_std_deg:
            label = "Uniform"
        elif circ_std_deg <= self._config.chaotic_std_deg:
            label = "Mixed"
        else:
            label = "Chaotic"

        dominant_heading_deg = math.degrees(
            math.atan2(mean_sin, mean_cos)
        ) % 360.0

        entropy = self._directional_entropy(moving)

        return FlowResult(
            label=label,
            confidence=mean_resultant_length,
            dominant_heading=dominant_heading_deg,
            entropy=entropy,
            direction_histogram=histogram,
        )

    @staticmethod
    def _direction_histogram(tracks: List[Track]) -> Dict[str, int]:
        """
        Raw count of tracks per compass direction, including
        Stationary. All 9 keys are always present (zero-filled) so
        downstream consumers don't need to guard against missing
        keys. This is a pure measurement -- no thresholding, no
        "reverse flow" or "dominant vs opposing" judgment applied.
        """
        histogram = {direction: 0 for direction in _ALL_DIRECTIONS}
        for track in tracks:
            if track.direction in histogram:
                histogram[track.direction] += 1
        return histogram

    @staticmethod
    def _directional_entropy(moving: List[Track]) -> float:
        counts = Counter(t.direction for t in moving if t.direction in _DIRECTION_TO_ANGLE_DEG)
        total = sum(counts.values())
        if total == 0:
            return 0.0

        entropy = 0.0
        for count in counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log(p)
        return entropy
