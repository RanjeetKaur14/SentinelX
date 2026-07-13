from typing import List

class RollingHeatmap:
    def __init__(
        self,
        rows: int,
        cols: int,
        decay_fast: float = 0.6,
        decay_slow: float = 0.95,
    ):
        """
        Args:
            rows, cols: grid dimensions, must match DensityConfig.
            decay_fast: retention factor for the short-memory
                accumulator -- reacts quickly to change.
            decay_slow: retention factor for the long-memory
                accumulator -- represents the "normal" baseline.
        """
        self._rows = rows
        self._cols = cols
        self._decay_fast = decay_fast
        self._decay_slow = decay_slow
        self._fast: List[List[float]] = [
            [0.0 for _ in range(cols)] for _ in range(rows)
        ]
        self._slow: List[List[float]] = [
            [0.0 for _ in range(cols)] for _ in range(rows)
        ]

    def update(self, instantaneous_grid: List[List[int]]) -> None:
      
        for r in range(self._rows):
            for c in range(self._cols):
                value = instantaneous_grid[r][c]
                self._fast[r][c] = (
                    self._decay_fast * self._fast[r][c]
                    + (1.0 - self._decay_fast) * value
                )
                self._slow[r][c] = (
                    self._decay_slow * self._slow[r][c]
                    + (1.0 - self._decay_slow) * value
                )

    def fast_heatmap(self, ndigits: int = 3) -> List[List[float]]:
        return [[round(v, ndigits) for v in row] for row in self._fast]

    def slow_heatmap(self, ndigits: int = 3) -> List[List[float]]:
        return [[round(v, ndigits) for v in row] for row in self._slow]

    def trend(self, ndigits: int = 3) -> List[List[float]]:
        """
        fast - slow, per cell. Positive and growing => that zone is
        heating up faster than its established baseline (an early
        surge/bottleneck indicator). Near zero => stable occupancy.
        Negative => that zone is cooling off relative to baseline.
        """
        return [
            [
                round(self._fast[r][c] - self._slow[r][c], ndigits)
                for c in range(self._cols)
            ]
            for r in range(self._rows)
        ]

    def as_rounded(self, ndigits: int = 3) -> List[List[float]]:
        return self.slow_heatmap(ndigits)

    def reset(self) -> None:
        self._fast = [[0.0 for _ in range(self._cols)] for _ in range(self._rows)]
        self._slow = [[0.0 for _ in range(self._cols)] for _ in range(self._rows)]
