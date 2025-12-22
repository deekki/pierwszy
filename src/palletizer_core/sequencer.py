from __future__ import annotations

from typing import Iterable, List, Tuple

from .models import Carton, Pallet

EPS = 1e-6

# Pattern is list of rectangles (x, y, w, l)
Pattern = List[Tuple[float, float, float, float]]


class EvenOddSequencer:
    """Decide the relative offset / rotation for odd layers."""

    def __init__(self, pattern: Pattern, carton: Carton, pallet: Pallet) -> None:
        self.pattern = pattern
        self.carton = carton
        self.pallet = pallet

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

        contact = 0.0
        perimeter = 0.0
        for x, y, w, length in candidate:
            perimeter += 2.0 * (w + length)
        for i, (x1, y1, w1, l1) in enumerate(candidate):
            for x2, y2, w2, l2 in candidate[i + 1 :]:
                if abs((x1 + w1) - x2) < EPS or abs((x2 + w2) - x1) < EPS:
                    overlap = max(0.0, min(y1 + l1, y2 + l2) - max(y1, y2))
                    contact += overlap
                if abs((y1 + l1) - y2) < EPS or abs((y2 + l2) - y1) < EPS:
                    overlap = max(0.0, min(x1 + w1, x2 + w2) - max(x1, x2))
                    contact += overlap
        contact_fraction = contact / perimeter if perimeter > EPS else 0.0

        edge_buffer = 0.0
        norm = max(1.0, min(self.carton.width, self.carton.length))
        for x, y, w, length in candidate:
            clearance = min(
                x,
                y,
                self.pallet.width - (x + w),
                self.pallet.length - (y + length),
            )
            edge_buffer += max(0.0, min(1.0, clearance / norm))
        edge_buffer /= len(candidate)

        mix_ratio = sum(
            1
            for _, _, w, length in candidate
            if (w >= length)
            != (self.carton.width >= self.carton.length)
        ) / len(candidate)

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
                    score = self._score_candidate(candidate, dx, dy)
                    if score > best_score + EPS:
                        best_score = score
                        best = candidate

        return even, best
