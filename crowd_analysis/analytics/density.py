

from typing import List, Dict, Tuple

from .config import DensityConfig
from .models import Track, Point


class DensityGrid:
    def __init__(self, config: DensityConfig):
        self._config = config

    def compute(
        self, tracks: List[Track], image_width: int, image_height: int
    ) -> Tuple[Dict[str, int], Dict[str, float], List[List[int]]]:
        """
        Returns:
            zone_density: dict mapping "zone_<row*cols + col + 1>" -> raw count
            normalized_zone_density: same keys -> count / cell_area_px
            heatmap: 2D list [row][col] -> raw count (matrix form of zone_density)
        """
        rows = self._config.grid_rows
        cols = self._config.grid_cols

        heatmap = [[0 for _ in range(cols)] for _ in range(rows)]

        cell_w = max(image_width, 1) / cols
        cell_h = max(image_height, 1) / rows
        cell_area = max(cell_w * cell_h, 1.0)

        for track in tracks:
            col = self._clamp(int(track.centroid[0] // cell_w), 0, cols - 1)
            row = self._clamp(int(track.centroid[1] // cell_h), 0, rows - 1)
            heatmap[row][col] += 1

        zone_density: Dict[str, int] = {}
        normalized_zone_density: Dict[str, float] = {}
        zone_num = 1
        for row in range(rows):
            for col in range(cols):
                count = heatmap[row][col]
                key = f"zone_{zone_num}"
                zone_density[key] = count
                normalized_zone_density[key] = count / cell_area
                zone_num += 1

        return zone_density, normalized_zone_density, heatmap

    @staticmethod
    def _clamp(value: int, low: int, high: int) -> int:
        return max(low, min(value, high))
