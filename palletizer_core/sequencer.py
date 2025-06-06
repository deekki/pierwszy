from __future__ import annotations

from typing import List, Tuple

from .models import Carton, Pallet

# Pattern is list of rectangles (x, y, w, l)
Pattern = List[Tuple[float, float, float, float]]


class EvenOddSequencer:
    """Decide the relative offset / rotation for odd layers."""

    def __init__(self, pattern: Pattern, carton: Carton, pallet: Pallet) -> None:
        self.pattern = pattern
        self.carton = carton
        self.pallet = pallet

    def _shift(self, pattern: Pattern, dx: float, dy: float) -> Pattern:
        """Return ``pattern`` translated by ``(dx, dy)``."""
        return [
            (x + dx, y + dy, width, length)
            for x, y, width, length in pattern
        ]

    def _mirror(self, pattern: Pattern, flip_x: bool, flip_y: bool) -> Pattern:
        """Mirror ``pattern`` across pallet axes if requested."""
        res: Pattern = []
        for x, y, w, l in pattern:
            nx = self.pallet.width - x - w if flip_x else x
            ny = self.pallet.length - y - l if flip_y else y
            res.append((nx, ny, w, l))
        return res

    def _fits(self, pattern: Pattern) -> bool:
        """Check if all cartons lie within pallet bounds."""
        return all(
            0 <= x
            and 0 <= y
            and x + width <= self.pallet.width
            and y + length <= self.pallet.length
            for x, y, width, length in pattern
        )

    def best_shift(self) -> Tuple[Pattern, Pattern]:
        """Return base and shifted layer with optional mirroring."""
        shifts = [
            (0.0, 0.0),
            (self.carton.width / 2, 0.0),
            (0.0, self.carton.length / 2),
            (self.carton.width / 2, self.carton.length / 2),
        ]

        # Try mirrored variants first
        for flip_x in (True, False):
            for flip_y in (True, False):
                if not flip_x and not flip_y:
                    # Skip the original orientation in this loop; handled later
                    continue
                base = self._mirror(self.pattern, flip_x, flip_y)
                for dx, dy in shifts:
                    candidate = self._shift(base, dx, dy)
                    if self._fits(candidate):
                        return base, candidate

        # Fall back to plain shifting of the original pattern
        for dx, dy in shifts:
            candidate = self._shift(self.pattern, dx, dy)
            if self._fits(candidate):
                return self.pattern, candidate

        # If everything fails, return the untouched pattern
        return self.pattern, self.pattern
