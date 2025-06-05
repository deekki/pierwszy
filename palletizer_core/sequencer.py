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

    def _shift(self, dx: float, dy: float) -> Pattern:
        return [
            (x + dx, y + dy, width, length)
            for x, y, width, length in self.pattern
        ]

    def best_shift(self) -> Tuple[Pattern, Pattern]:
        """Return even and best odd layer."""
        even = self.pattern
        shifts = [
            (0.0, 0.0),
            (self.carton.width / 2, 0.0),
            (0.0, self.carton.length / 2),
            (self.carton.width / 2, self.carton.length / 2),
        ]
        best: Pattern | None = None
        for dx, dy in shifts:
            candidate = self._shift(dx, dy)
            if all(
                0 <= x
                and 0 <= y
                and x + width <= self.pallet.width
                and y + length <= self.pallet.length
                for x, y, width, length in candidate
            ):
                best = candidate
                break
        if best is None:
            best = even
        return even, best
