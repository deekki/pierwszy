from __future__ import annotations

from typing import List, Tuple

LayerLayout = List[Tuple[float, float, float, float]]


def layout_signature(layout: LayerLayout, eps: float = 1e-6) -> tuple:
    rounded = []
    for x, y, w, l in layout:
        rounded.append(
            (
                round(x / eps) * eps,
                round(y / eps) * eps,
                round(w / eps) * eps,
                round(l / eps) * eps,
            )
        )
    return tuple(sorted(rounded))
