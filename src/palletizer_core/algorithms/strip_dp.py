from __future__ import annotations

from typing import Dict, List, Tuple

from palletizer_core.signature import layout_signature

LayerLayout = List[Tuple[float, float, float, float]]


def _build_strip_sequence(count_a: int, count_b: int, prefer_a: bool) -> List[str]:
    sequence: List[str] = []
    remaining = {"A": count_a, "B": count_b}
    order = ["A", "B"] if prefer_a else ["B", "A"]
    while remaining["A"] > 0 or remaining["B"] > 0:
        for key in order:
            if remaining[key] > 0:
                sequence.append(key)
                remaining[key] -= 1
    return sequence


def _build_strip_layout(
    strip_sequence: List[str],
    strip_specs: Dict[str, Tuple[float, float, float, int]],
) -> LayerLayout:
    layout: LayerLayout = []
    cursor_x = 0.0
    for key in strip_sequence:
        strip_width, box_w, box_l, boxes_per_strip = strip_specs[key]
        for idx in range(boxes_per_strip):
            y = idx * box_l
            layout.append((cursor_x, y, box_w, box_l))
        cursor_x += strip_width
    return layout


def _strip_variants(
    pallet_w: float,
    pallet_l: float,
    box_w: float,
    box_l: float,
    max_variants: int,
) -> List[LayerLayout]:
    if pallet_w <= 0 or pallet_l <= 0 or box_w <= 0 or box_l <= 0:
        return []

    strip_specs: Dict[str, Tuple[float, float, float, int]] = {}
    boxes_a = int(pallet_l // box_l) if box_l > 0 else 0
    if boxes_a > 0:
        strip_specs["A"] = (box_w, box_w, box_l, boxes_a)

    boxes_b = int(pallet_l // box_w) if box_w > 0 else 0
    if abs(box_w - box_l) > 1e-6 and boxes_b > 0:
        strip_specs["B"] = (box_l, box_l, box_w, boxes_b)

    if not strip_specs:
        return []

    max_a = int(pallet_w // strip_specs["A"][0]) if "A" in strip_specs else 0
    max_b = int(pallet_w // strip_specs["B"][0]) if "B" in strip_specs else 0

    combos: List[Tuple[int, float, int, int]] = []
    for count_a in range(max_a + 1):
        for count_b in range(max_b + 1):
            if count_a == 0 and count_b == 0:
                continue
            width = 0.0
            count = 0
            if count_a:
                strip_width, _, _, per_strip = strip_specs["A"]
                width += count_a * strip_width
                count += count_a * per_strip
            if count_b:
                strip_width, _, _, per_strip = strip_specs["B"]
                width += count_b * strip_width
                count += count_b * per_strip
            if width <= pallet_w + 1e-6 and count > 0:
                combos.append((count, width, count_a, count_b))

    combos.sort(key=lambda item: (-item[0], -item[1], -item[2], -item[3]))

    layouts: List[LayerLayout] = []
    seen = set()
    for count, _, count_a, count_b in combos:
        if count <= 0:
            continue
        prefer_a = count_a >= count_b
        sequence = _build_strip_sequence(count_a, count_b, prefer_a)
        layout = _build_strip_layout(sequence, strip_specs)
        signature = layout_signature(layout)
        if signature not in seen:
            layouts.append(layout)
            seen.add(signature)
        if count_a > 0 and count_b > 0 and len(layouts) < max_variants:
            alternate = _build_strip_sequence(count_a, count_b, not prefer_a)
            alt_layout = _build_strip_layout(alternate, strip_specs)
            alt_signature = layout_signature(alt_layout)
            if alt_signature not in seen:
                layouts.append(alt_layout)
                seen.add(alt_signature)
        if len(layouts) >= max_variants:
            break

    return layouts


def generate_strip_layouts(
    pallet_w: float,
    pallet_l: float,
    box_w: float,
    box_l: float,
    *,
    max_variants: int = 20,
) -> List[LayerLayout]:
    layouts = _strip_variants(pallet_w, pallet_l, box_w, box_l, max_variants)
    swapped = _strip_variants(pallet_l, pallet_w, box_l, box_w, max_variants)
    for layout in swapped:
        layouts.append([(y, x, length, w) for x, y, w, length in layout])

    deduped: List[LayerLayout] = []
    seen = set()
    for layout in layouts:
        signature = layout_signature(layout)
        if signature in seen:
            continue
        deduped.append(layout)
        seen.add(signature)
        if len(deduped) >= max_variants:
            break
    return deduped
