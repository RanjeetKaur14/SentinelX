"""
test_heatmap.py
----------------
Covers RollingHeatmap: fast/slow decay correctness, trend sign,
long-running saturation behavior, and basic memory-shape stability.
"""

import pytest

from analytics.heatmap import RollingHeatmap


class TestDecayBasics:
    def test_starts_at_zero(self):
        rh = RollingHeatmap(rows=2, cols=2)
        assert rh.fast_heatmap() == [[0.0, 0.0], [0.0, 0.0]]
        assert rh.slow_heatmap() == [[0.0, 0.0], [0.0, 0.0]]
        assert rh.trend() == [[0.0, 0.0], [0.0, 0.0]]

    def test_fast_reacts_quicker_than_slow(self):
        rh = RollingHeatmap(rows=1, cols=1, decay_fast=0.5, decay_slow=0.95)
        rh.update([[10]])
        # After one update, fast (lower decay = faster reaction) should
        # be closer to the new value than slow.
        assert rh.fast_heatmap()[0][0] > rh.slow_heatmap()[0][0]

    def test_trend_is_fast_minus_slow(self):
        rh = RollingHeatmap(rows=1, cols=1, decay_fast=0.5, decay_slow=0.95)
        rh.update([[10]])
        fast = rh.fast_heatmap()[0][0]
        slow = rh.slow_heatmap()[0][0]
        trend = rh.trend()[0][0]
        assert trend == pytest.approx(fast - slow, abs=1e-6)

    def test_sustained_zero_input_decays_to_zero(self):
        rh = RollingHeatmap(rows=1, cols=1)
        rh.update([[50]])
        for _ in range(200):
            rh.update([[0]])
        assert rh.fast_heatmap()[0][0] == pytest.approx(0.0, abs=1e-6)
        assert rh.slow_heatmap()[0][0] == pytest.approx(0.0, abs=1e-6)


class TestLongRunningSaturation:
    def test_converges_to_sustained_input_without_overflow(self):
        rh = RollingHeatmap(rows=4, cols=4, decay_fast=0.6, decay_slow=0.95)
        grid = [[0] * 4 for _ in range(4)]
        grid[0][0] = 500  # sustained extreme density in one cell
        for _ in range(10000):
            rh.update(grid)
        assert rh.fast_heatmap()[0][0] == pytest.approx(500.0, abs=0.01)
        assert rh.slow_heatmap()[0][0] == pytest.approx(500.0, abs=0.01)
        assert rh.trend()[0][0] == pytest.approx(0.0, abs=0.01)

    def test_ten_thousand_updates_does_not_grow_unbounded(self):
        """Guards against exponential-smoothing math regressing into
        an accumulator (sum) instead of a blend -- which would grow
        without bound over a long-running session."""
        rh = RollingHeatmap(rows=2, cols=2, decay_fast=0.9, decay_slow=0.99)
        for i in range(10000):
            rh.update([[1, 0], [0, 0]])
        assert rh.fast_heatmap()[0][0] <= 1.0 + 1e-6
        assert rh.slow_heatmap()[0][0] <= 1.0 + 1e-6


class TestShapeStability:
    def test_alias_as_rounded_matches_slow_heatmap(self):
        rh = RollingHeatmap(rows=2, cols=2)
        rh.update([[3, 1], [0, 2]])
        assert rh.as_rounded() == rh.slow_heatmap()

    def test_reset_zeros_everything(self):
        rh = RollingHeatmap(rows=2, cols=2)
        rh.update([[3, 1], [0, 2]])
        rh.reset()
        assert rh.fast_heatmap() == [[0.0, 0.0], [0.0, 0.0]]
        assert rh.slow_heatmap() == [[0.0, 0.0], [0.0, 0.0]]
