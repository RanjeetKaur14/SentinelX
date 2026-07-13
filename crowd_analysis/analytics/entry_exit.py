

from typing import Dict, List

from .config import EntryExitConfig, EntryExitLine
from .models import Track, Point


def _line_length(line: EntryExitLine) -> float:
    x1, y1 = line.p1
    x2, y2 = line.p2
    return max(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5, 1e-9)


def _signed_side(line: EntryExitLine, point: Point) -> float:
    
    x1, y1 = line.p1
    x2, y2 = line.p2
    px, py = point

    line_vec = (x2 - x1, y2 - y1)
    point_vec = (px - x1, py - y1)

    return line_vec[0] * point_vec[1] - line_vec[1] * point_vec[0]


class EntryExitCounter:
    def __init__(self, config: EntryExitConfig):
        self._config = config
        self._entry_count = 0
        self._exit_count = 0
        
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
        return {
            "entry_count": self._entry_count,
            "exit_count": self._exit_count,
            "per_line": {
                name: dict(stats) for name, stats in self._per_line.items()
            },
        }
