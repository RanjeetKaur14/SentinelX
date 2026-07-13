"""
entry_exit.py
-------------
Configurable virtual line-crossing counter.

Each line is defined by two endpoints. For every track we determine
which "side" of the line its centroid is on using the sign of the 2D
cross product of (line_vector, point_vector). When a track's side
flips between consecutive frames, that's a crossing.

Sign convention: with `line_vec = p2 - p1`, walking along the line
from p1 to p2, the "positive" side is to the *left* of that direction
of travel (standard right-hand-rule cross product in image
coordinates). A crossing from positive -> negative is counted as an
ENTRY, negative -> positive as an EXIT. Choose `p1`/`p2` ordering per
line so this matches the physical venue layout; `direction_in` on
`EntryExitLine` is a human-readable label to help keep that straight
when defining lines in config.

v1 -> v2 changes:
    1. Hysteresis banding -- a track's cached "side" only updates once
       its perpendicular distance from the line exceeds
       `hysteresis_distance_px`. This kills oscillation double-counts
       from tracks lingering near the line (very common at 30fps with
       real camera noise), which was a real correctness gap in v1's
       bare "!= 0.0" guard.
    2. Per-line statistics -- entry/exit counts are now tracked both
       globally and per named line, since a bottleneck forming at one
       specific entrance is a very different risk signal than
       distributed flow across several entrances.
"""

from typing import Dict, List

from .config import EntryExitConfig, EntryExitLine
from .models import Track, Point


def _line_length(line: EntryExitLine) -> float:
    x1, y1 = line.p1
    x2, y2 = line.p2
    return max(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5, 1e-9)


def _signed_side(line: EntryExitLine, point: Point) -> float:
    """
    Returns a signed scalar proportional to perpendicular distance:
    positive on one side of the line, negative on the other, ~0
    exactly on the line. (Raw cross product -- see `_perpendicular_
    distance` for the normalized version used in hysteresis gating.)
    """
    x1, y1 = line.p1
    x2, y2 = line.p2
    px, py = point

    line_vec = (x2 - x1, y2 - y1)
    point_vec = (px - x1, py - y1)

    return line_vec[0] * point_vec[1] - line_vec[1] * point_vec[0]


class EntryExitCounter:
    """
    Tracks cumulative entry/exit counts across all configured lines,
    both globally and per line. Stateless with respect to full
    history -- only needs each track's previous side, which is cached
    on the Track object itself (`last_line_side`) so no separate
    bookkeeping dict is required.
    """

    def __init__(self, config: EntryExitConfig):
        self._config = config
        self._entry_count = 0
        self._exit_count = 0
        # Per-line breakdown, keyed by line name.
        self._per_line: Dict[str, Dict[str, int]] = {
            line.name: {"entry_count": 0, "exit_count": 0}
            for line in config.lines
        }
        self._line_lengths: Dict[str, float] = {
            line.name: _line_length(line) for line in config.lines
        }

    @property
    def entry_count(self) -> int:
        return self._entry_count

    @property
    def exit_count(self) -> int:
        return self._exit_count

    def update(self, tracks: List[Track]) -> None:
        if not self._config.lines:
            return

        for track in tracks:
            for line in self._config.lines:
                raw_side = _signed_side(line, track.centroid)
                line_length = self._line_lengths[line.name]
                perpendicular_distance = abs(raw_side) / line_length

                # Only a confidently-observed side (outside the
                # hysteresis band) is eligible to participate in
                # crossing detection at all. A track lingering inside
                # the band simply doesn't get evaluated this frame --
                # its cached side (and crossing eligibility) is
                # untouched until it clears the band, which is what
                # actually prevents the double-count: we never react
                # to an ambiguous, near-the-line reading.
                if perpendicular_distance < self._config.hysteresis_distance_px:
                    continue

                previous_side = track.last_line_side.get(line.name)

                if previous_side is not None and previous_side != 0.0:
                    crossed_positive_to_negative = (
                        previous_side > 0 and raw_side < 0
                    )
                    crossed_negative_to_positive = (
                        previous_side < 0 and raw_side > 0
                    )

                    if crossed_positive_to_negative:
                        self._entry_count += 1
                        self._per_line[line.name]["entry_count"] += 1
                    elif crossed_negative_to_positive:
                        self._exit_count += 1
                        self._per_line[line.name]["exit_count"] += 1
                    # else: no crossing this frame.

                track.last_line_side[line.name] = raw_side

    def snapshot(self) -> Dict[str, object]:
        """
        Returns global counts (unchanged keys from v1, so existing
        consumers of `entry_count`/`exit_count` keep working) plus a
        new `per_line` breakdown.
        """
        return {
            "entry_count": self._entry_count,
            "exit_count": self._exit_count,
            "per_line": {
                name: dict(stats) for name, stats in self._per_line.items()
            },
        }
