from __future__ import annotations

import math
from typing import List, Tuple

# Pattern is list of rectangles (x, y, w, l)
Pattern = List[Tuple[float, float, float, float]]


def compute_edge_contact_fraction(
    pattern: Pattern, *, eps: float = 1e-6, clamp: bool = True
) -> float:
    if not pattern:
        return 0.0
    perimeter = 0.0
    contact = 0.0
    n = len(pattern)
    for _, _, w, length in pattern:
        perimeter += 2.0 * (w + length)
    for i in range(n):
        x1, y1, w1, l1 = pattern[i]
        for j in range(i + 1, n):
            x2, y2, w2, l2 = pattern[j]
            if abs((x1 + w1) - x2) < eps or abs((x2 + w2) - x1) < eps:
                overlap = max(0.0, min(y1 + l1, y2 + l2) - max(y1, y2))
                contact += overlap
            if abs((y1 + l1) - y2) < eps or abs((y2 + l2) - y1) < eps:
                overlap = max(0.0, min(x1 + w1, x2 + w2) - max(x1, x2))
                contact += overlap
    if perimeter <= eps:
        return 0.0
    value = contact / perimeter
    if not clamp:
        return value
    return max(0.0, min(1.0, value))


def compute_edge_buffer_metrics(
    pattern: Pattern, pallet_w: float, pallet_l: float, norm: float
) -> Tuple[float, float]:
    if not pattern:
        return 0.0, 0.0
    acc = 0.0
    min_clearance = float("inf")
    for x, y, w, length in pattern:
        clearance = min(
            x,
            y,
            pallet_w - (x + w),
            pallet_l - (y + length),
        )
        min_clearance = min(min_clearance, clearance)
        acc += max(0.0, min(1.0, clearance / norm))
    if math.isinf(min_clearance):
        min_clearance = 0.0
    return acc / len(pattern), min_clearance


def compute_edge_buffer_score(
    pattern: Pattern, pallet_w: float, pallet_l: float, norm: float
) -> float:
    buffer_score, _ = compute_edge_buffer_metrics(pattern, pallet_w, pallet_l, norm)
    return buffer_score


def compute_orientation_mix(pattern: Pattern, *, default_orientation: bool) -> float:
    if not pattern:
        return 0.0
    rotated = 0
    for _, _, w, length in pattern:
        if (w >= length) != default_orientation:
            rotated += 1
    return rotated / len(pattern)


def compute_cube_efficiency(
    *,
    cartons_per_layer: int,
    layers: int,
    box_w_ext: float,
    box_l_ext: float,
    box_h_ext: float,
    pallet_w: float,
    pallet_l: float,
    max_stack: float = 0.0,
    pallet_h: float = 0.0,
    include_pallet_height: bool = False,
) -> float:
    """Return used carton volume divided by usable palletizing volume."""
    values = [cartons_per_layer, layers, box_w_ext, box_l_ext, box_h_ext, pallet_w, pallet_l]
    if any(v is None for v in values) or min(float(v) for v in values) <= 0:
        return 0.0
    usable_h = 0.0
    if max_stack and max_stack > 0:
        usable_h = float(max_stack) - (float(pallet_h) if include_pallet_height else 0.0)
    if usable_h <= 0:
        usable_h = float(layers) * float(box_h_ext)
    available = float(pallet_w) * float(pallet_l) * usable_h
    if available <= 0:
        return 0.0
    used = (
        float(cartons_per_layer)
        * float(layers)
        * float(box_w_ext)
        * float(box_l_ext)
        * float(box_h_ext)
    )
    return max(0.0, min(1.0, used / available))
