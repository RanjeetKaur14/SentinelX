"""
test_density.py
----------------
Covers DensityGrid: empty frames, single/many people, grid-boundary
placement, out-of-frame detections, and extreme/changing resolutions.
"""

import pytest

from analytics.config import DensityConfig
from analytics.density import DensityGrid
from analytics.models import Track


def make_track(track_id, cx, cy):
    return Track(track_id=track_id, bbox=(cx - 10, cy - 10, cx + 10, cy + 10), centroid=(cx, cy))


class TestBasicCounts:
    def test_empty_track_list_gives_all_zero_grid(self):
        grid = DensityGrid(DensityConfig(grid_rows=4, grid_cols=4))
        density, normalized, heatmap = grid.compute([], 1920, 1080)
        assert all(v == 0 for v in density.values())
        assert all(v == 0.0 for v in normalized.values())
        assert sum(sum(row) for row in heatmap) == 0

    def test_single_person_counted_once(self):
        grid = DensityGrid(DensityConfig(grid_rows=4, grid_cols=4))
        density, _, heatmap = grid.compute([make_track(0, 960, 540)], 1920, 1080)
        assert sum(density.values()) == 1
        assert sum(sum(row) for row in heatmap) == 1

    def test_hundred_people_all_counted(self):
        grid = DensityGrid(DensityConfig(grid_rows=4, grid_cols=4))
        tracks = [make_track(i, (i * 17) % 1920, (i * 31) % 1080) for i in range(100)]
        density, _, heatmap = grid.compute(tracks, 1920, 1080)
        assert sum(density.values()) == 100
        assert sum(sum(row) for row in heatmap) == 100

    def test_normalized_density_matches_raw_over_cell_area(self):
        grid = DensityGrid(DensityConfig(grid_rows=4, grid_cols=4))
        density, normalized, _ = grid.compute([make_track(0, 960, 540)], 1920, 1080)
        cell_area = (1920 / 4) * (1080 / 4)
        assert normalized["zone_11"] == pytest.approx(density["zone_11"] / cell_area)


class TestBoundariesAndOutOfFrame:
    def test_person_exactly_on_grid_boundary_assigned_consistently(self):
        grid = DensityGrid(DensityConfig(grid_rows=4, grid_cols=4))
        # x=480 is exactly the boundary between column 0 and 1 for a
        # 1920-wide, 4-col grid (cell width 480).
        density, _, _ = grid.compute([make_track(0, 480, 540)], 1920, 1080)
        assert sum(density.values()) == 1  # counted exactly once, no double count

    def test_person_outside_frame_still_counted_via_clamping(self):
        grid = DensityGrid(DensityConfig(grid_rows=4, grid_cols=4))
        density, _, _ = grid.compute([make_track(0, 5000, -500)], 1920, 1080)
        assert sum(density.values()) == 1  # clamped into an edge cell, not dropped or crashed

    def test_far_negative_coordinates_do_not_crash(self):
        grid = DensityGrid(DensityConfig(grid_rows=4, grid_cols=4))
        density, _, _ = grid.compute([make_track(0, -99999, -99999)], 1920, 1080)
        assert sum(density.values()) == 1


class TestResolutionExtremes:
    def test_very_wide_image(self):
        grid = DensityGrid(DensityConfig(grid_rows=4, grid_cols=4))
        density, _, _ = grid.compute([make_track(0, 50000, 1)], 100000, 1)
        assert sum(density.values()) == 1

    def test_very_tall_image(self):
        grid = DensityGrid(DensityConfig(grid_rows=4, grid_cols=4))
        density, _, _ = grid.compute([make_track(0, 1, 50000)], 1, 100000)
        assert sum(density.values()) == 1

    def test_zero_size_image_does_not_crash(self):
        grid = DensityGrid(DensityConfig(grid_rows=4, grid_cols=4))
        density, _, _ = grid.compute([make_track(0, 0, 0)], 0, 0)
        assert sum(density.values()) == 1

    def test_grid_rows_or_cols_zero_rejected_at_config_time(self):
        with pytest.raises(ValueError):
            DensityConfig(grid_rows=0, grid_cols=4)
        with pytest.raises(ValueError):
            DensityConfig(grid_rows=4, grid_cols=0)
