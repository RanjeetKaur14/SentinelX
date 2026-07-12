"""
flow.py
-------
Classifies overall crowd movement pattern as "Uniform", "Mixed", or
"Chaotic" based on the circular spread of moving tracks' headings, and
now also exposes the underlying continuous statistics that used to be
computed and thrown away.

Approach:
    1. Filter to tracks that are actually moving (direction != Stationary).
    2. Convert each track's direction to a heading angle in radians.
    3. Compute the circular standard deviation of those headings using
       the mean resultant length (standard directional-statistics
       technique) -- cheap, no trig-heavy per-pair comparisons needed.
       The mean resultant length R (0..1) doubles as a natural
       "flow confidence" score: R close to 1 means headings agree
       strongly (confident dominant direction), R close to 0 means
       they're scattered.
    4. Threshold the circular std-dev against config to pick a label.
    5. Separately, bucket moving tracks into the same 8 compass bins
       used elsewhere in the codebase and compute Shannon entropy over
       that histogram. This is a different signal from circular
       std-dev -- it catches multi-modal chaos (e.g. two opposing
       streams, which can have a *low* circular std-dev around either
       mode individually but is still a genuinely chaotic/conflicting
       flow pattern) that a single-mode statistic like std-dev can
       under-represent.
    6. Also build a raw `direction_histogram` over ALL tracks (moving
       and Stationary) -- this is a plain measurement, not an
       interpretation. It deliberately does NOT compute anything like
       "reverse flow" from the histogram; a downstream Risk Prediction
       Engine can derive that (or any other judgment call) from the
       raw counts itself.

Low spread / high confidence -> "Uniform" (everyone moving the same
    way -- notably, this is the *dangerous* pattern for stampede risk
    when combined with high density/congestion, since it indicates a
    directional surge, not necessarily a safe pattern).
Medium spread -> "Mixed" (a couple of distinct flow streams).
High spread -> "Chaotic" (people moving in all directions, or
    conflicting streams -- also a stampede-risk signal, panic/disorder).
"""

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
    """Stateless classifier -- recomputes from the current track set each frame."""

    def __init__(self, config: FlowConfig):
        self._config = config

    def classify(self, tracks: List[Track]) -> FlowResult:
        moving = [t for t in tracks if t.direction != "Stationary"]
        histogram = self._direction_histogram(tracks)

        if len(moving) < self._config.min_moving_tracks:
            # Not enough motion to call it anything else -- also not
            # enough for a meaningful confidence/heading/entropy read.
            # The histogram is still a valid raw measurement, so it's
            # still returned.
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
        # Clamp for numerical safety before log/sqrt.
        clamped_r = min(max(mean_resultant_length, 1e-9), 1.0)

        # Circular standard deviation (radians), standard formula.
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
        """
        Shannon entropy (natural log, nats) over the 8-bin compass
        histogram of moving tracks' directions. O(n) to bin + O(8) for
        the entropy sum -- negligible cost.

        0.0 = all moving tracks share one direction (fully ordered).
        ln(8) ~= 2.079 = tracks spread perfectly evenly across all 8
        directions (fully disordered) -- e.g. two opposing streams or
        a genuinely chaotic crowd can push this high even when
        circular std-dev alone might read as only moderately spread.
        """
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
