from __future__ import annotations

from typing import Iterable, List, Tuple

from .metrics import (
    compute_edge_buffer_score,
    compute_edge_contact_fraction,
    compute_orientation_mix,
)
from .models import Carton, Pallet
from .support import min_support_fraction as layer_min_support

EPS = 1e-6

# Pattern is list of rectangles (x, y, w, l)
Pattern = List[Tuple[float, float, float, float]]


class EvenOddSequencer:
    """Decide the relative offset / rotation for odd layers."""

    def __init__(
        self,
        pattern: Pattern,
        carton: Carton,
        pallet: Pallet,
        *,
        allow_offsets: bool = False,
        min_support: float = 0.80,
        assume_full_support: bool = False,
    ) -> None:
        self.pattern = pattern
        self.carton = carton
        self.pallet = pallet
        self.allow_offsets = allow_offsets
        self.min_support = min_support
        self.assume_full_support = assume_full_support

    def _shift_pattern(self, pattern: Pattern, dx: float, dy: float) -> Pattern:
        return [(x + dx, y + dy, width, length) for x, y, width, length in pattern]

    @staticmethod
    def _rotate_pattern(pattern: Pattern) -> Pattern:
        rotated: Pattern = []
        for x, y, width, length in pattern:
            if abs(width - length) < EPS:
                rotated.append((x, y, width, length))
                continue
            cx = x + width / 2
            cy = y + length / 2
            new_w, new_l = length, width
            new_x = cx - new_w / 2
            new_y = cy - new_l / 2
            rotated.append((new_x, new_y, new_w, new_l))
        return rotated

    def _generate_offsets(self, limit_neg: float, limit_pos: float, pitch: float) -> Iterable[float]:
        yield 0.0
        if limit_neg <= EPS and limit_pos <= EPS:
            return
        step = max(pitch / 2.0, 1.0) if pitch > EPS else max(limit_neg, limit_pos, 1.0)
        k = 1
        while k * step <= limit_pos + EPS:
            yield round(min(limit_pos, k * step), 4)
            k += 1
        k = 1
        while k * step <= limit_neg + EPS:
            yield round(-min(limit_neg, k * step), 4)
            k += 1
        yield round(limit_pos, 4)
        yield round(-limit_neg, 4)

    def _is_valid(self, pattern: Pattern) -> bool:
        for x, y, width, length in pattern:
            if (
                x < -EPS
                or y < -EPS
                or x + width > self.pallet.width + EPS
                or y + length > self.pallet.length + EPS
            ):
                return False
        for i, a in enumerate(pattern):
            ax, ay, aw, al = a
            for b in pattern[i + 1 :]:
                bx, by, bw, bl = b
                if not (
                    ax + aw <= bx + EPS
                    or bx + bw <= ax + EPS
                    or ay + al <= by + EPS
                    or by + bl <= ay + EPS
                ):
                    return False
        return True

    def _score_candidate(self, candidate: Pattern, dx: float, dy: float) -> float:
        if not candidate:
            return -1.0
        interlock = 0.0
        if self.carton.width > 0:
            interlock += min(1.0, abs(dx) / self.carton.width)
        if self.carton.length > 0:
            interlock += min(1.0, abs(dy) / self.carton.length)
        interlock /= 2.0

        contact_fraction = compute_edge_contact_fraction(
            candidate, eps=EPS, clamp=False
        )

        norm = max(1.0, min(self.carton.width, self.carton.length))
        edge_buffer = compute_edge_buffer_score(
            candidate, self.pallet.width, self.pallet.length, norm
        )

        mix_ratio = compute_orientation_mix(
            candidate, default_orientation=self.carton.width >= self.carton.length
        )

        return (
            0.4 * interlock
            + 0.3 * contact_fraction
            + 0.2 * edge_buffer
            + 0.1 * mix_ratio
        )

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

        dx_options = list(self._generate_offsets(max_left, max_right, self.carton.width))
        dy_options = list(self._generate_offsets(max_down, max_up, self.carton.length))
        if self.allow_offsets:
            half_width = round(self.carton.width / 2.0, 4) if self.carton.width > 0 else 0.0
            half_length = (
                round(self.carton.length / 2.0, 4) if self.carton.length > 0 else 0.0
            )
            if half_width > EPS:
                if half_width <= max_right + EPS:
                    dx_options.append(half_width)
                if half_width <= max_left + EPS:
                    dx_options.append(-half_width)
            if half_length > EPS:
                if half_length <= max_up + EPS:
                    dy_options.append(half_length)
                if half_length <= max_down + EPS:
                    dy_options.append(-half_length)

        dx_options = list(dict.fromkeys(dx_options))
        dy_options = list(dict.fromkeys(dy_options))

        candidates: List[Pattern] = [even]
        rotated = self._rotate_pattern(self.pattern)
        if rotated != self.pattern:
            candidates.append(rotated)

        best = even
        best_score = -1.0
        for base_pattern in candidates:
            for dx in dx_options:
                for dy in dy_options:
                    candidate = self._shift_pattern(base_pattern, dx, dy)
                    if not self._is_valid(candidate):
                        continue
                    if self.allow_offsets and not self.assume_full_support:
                        support = layer_min_support(candidate, even)
                        if support < self.min_support:
                            continue
                    score = self._score_candidate(candidate, dx, dy)
                    if score > best_score + EPS:
                        best_score = score
                        best = candidate

        return even, best
