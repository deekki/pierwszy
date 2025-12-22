from __future__ import annotations

from typing import List, Tuple

LayerLayout = List[Tuple[float, float, float, float]]


def rect_area(rect: Tuple[float, float, float, float]) -> float:
    _, _, w, l = rect
    return max(0.0, w) * max(0.0, l)


def rect_intersection_area(
    a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]
) -> float:
    ax, ay, aw, al = a
    bx, by, bw, bl = b
    overlap_w = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    overlap_l = max(0.0, min(ay + al, by + bl) - max(ay, by))
    return overlap_w * overlap_l


def support_fraction_per_box(
    layer_above: LayerLayout, layer_below: LayerLayout
) -> List[float]:
    support_values: List[float] = []
    for box in layer_above:
        area = rect_area(box)
        if area <= 0:
            support_values.append(0.0)
            continue
        supported_area = sum(rect_intersection_area(box, below) for below in layer_below)
        support_values.append(min(1.0, supported_area / area))
    return support_values


def min_support_fraction(layer_above: LayerLayout, layer_below: LayerLayout) -> float:
    support_values = support_fraction_per_box(layer_above, layer_below)
    return min(support_values) if support_values else 0.0


def avg_support_fraction(layer_above: LayerLayout, layer_below: LayerLayout) -> float:
    support_values = support_fraction_per_box(layer_above, layer_below)
    return sum(support_values) / len(support_values) if support_values else 0.0
