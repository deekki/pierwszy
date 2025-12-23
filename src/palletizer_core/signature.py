from __future__ import annotations

from typing import List, Tuple

LayerLayout = List[Tuple[float, float, float, float]]


def canonicalize(layout: LayerLayout, eps: float = 1e-6) -> LayerLayout:
    if not layout:
        return []
    min_x = min(x for x, _, _, _ in layout)
    min_y = min(y for _, y, _, _ in layout)
    canonical = []
    for x, y, w, length in layout:
        canonical.append(
            (
                round((x - min_x) / eps) * eps,
                round((y - min_y) / eps) * eps,
                round(w / eps) * eps,
                round(length / eps) * eps,
            )
        )
    return sorted(canonical, key=lambda item: (item[1], item[0], item[3], item[2]))


def layout_signature(layout: LayerLayout, eps: float = 1e-6) -> tuple:
    return tuple(canonicalize(layout, eps=eps))
