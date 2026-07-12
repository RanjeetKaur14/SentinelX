"""
density.py
----------
Divides the frame into a configurable grid and counts people per cell.

This underpins both `density` (named zones) and `heatmap` (raw 2D
occupancy matrix) in the final output -- both are derived from the
same single pass over track centroids to avoid duplicate work.

v1 -> v2 change: also returns *normalized* density (people / cell
area in px^2) alongside the existing raw counts. Raw counts alone
aren't comparable across cameras or grid configurations -- a 4x4 grid
on a 1920x1080 feed has different cell areas than an 8x8 grid on a
640x480 feed, so "12 people in zone_1" means different things in each
case. Normalized density is a single division per cell (already-known
cell area), so it's effectively free.
"""

from typing import List, Dict, Tuple

from .config import DensityConfig
from .models import Track, Point


class DensityGrid:
    """Computes per-cell occupancy counts for a set of centroids."""

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
