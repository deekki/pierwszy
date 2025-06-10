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
        """Return even and best odd layer.

        The method inspects how much space surrounds the base layer and then
        tries shifting the odd layer within that clearance.  The offset that
        yields the strongest interlock while keeping all cartons on the pallet
        is selected.

        Examples
        --------
        >>> patt = [(0, 0, 100, 100), (100, 0, 100, 100)]
        >>> seq = EvenOddSequencer(patt, Carton(100, 100), Pallet(220, 100))
        >>> even, odd = seq.best_shift()
        >>> odd[0][:2]
        (10.0, 0.0)
        """
        even = self.pattern

        # Compute free space around the base pattern.
        min_x = min(x for x, _, _, _ in self.pattern)
        max_x = max(x + w for x, _, w, _ in self.pattern)
        min_y = min(y for _, y, _, _ in self.pattern)
        max_y = max(y + length for _, y, _, length in self.pattern)

        left = min_x
        right = self.pallet.width - max_x
        bottom = min_y
        top = self.pallet.length - max_y

        # Maximum feasible shift in each direction (never more than half a box).
        max_left = min(self.carton.width / 2, left)
        max_right = min(self.carton.width / 2, right)
        max_down = min(self.carton.length / 2, bottom)
        max_up = min(self.carton.length / 2, top)

        dx_options = {0.0}
        dy_options = {0.0}
        if max_left > 0:
            dx_options.add(-max_left)
        if max_right > 0:
            dx_options.add(max_right)
        if max_down > 0:
            dy_options.add(-max_down)
        if max_up > 0:
            dy_options.add(max_up)

        best = even
        best_score = -1.0
        for dx in sorted(dx_options):
            for dy in sorted(dy_options):
                candidate = self._shift(dx, dy)
                if not all(
                    0 <= x
                    and 0 <= y
                    and x + width <= self.pallet.width
                    and y + length <= self.pallet.length
                    for x, y, width, length in candidate
                ):
                    continue
                score = abs(dx) + abs(dy)
                if score > best_score:
                    best_score = score
                    best = candidate

        return even, best
