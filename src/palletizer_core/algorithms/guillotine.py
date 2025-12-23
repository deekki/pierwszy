from __future__ import annotations

from typing import Dict, List, Tuple

from palletizer_core.signature import layout_signature

LayerLayout = List[Tuple[float, float, float, float]]


def _grid_layout_int(
    rect_w: int, rect_l: int, box_w: int, box_l: int
) -> List[Tuple[int, int, int, int]]:
    cols = rect_w // box_w if box_w > 0 else 0
    rows = rect_l // box_l if box_l > 0 else 0
    layout: List[Tuple[int, int, int, int]] = []
    for i in range(cols):
        for j in range(rows):
            layout.append((i * box_w, j * box_l, box_w, box_l))
    return layout


def _layout_score(layout: List[Tuple[int, int, int, int]]) -> Tuple[int, int]:
    count = len(layout)
    area = sum(w * length for _, _, w, length in layout)
    return count, area


def generate_guillotine_layouts(
    pallet_w: float,
    pallet_l: float,
    box_w: float,
    box_l: float,
    *,
    max_variants: int = 30,
    max_depth: int = 3,
    per_split_limit: int = 6,
) -> List[LayerLayout]:
    if pallet_w <= 0 or pallet_l <= 0 or box_w <= 0 or box_l <= 0:
        return []

    scale = 1000
    pw = int(round(pallet_w * scale))
    pl = int(round(pallet_l * scale))
    bw = int(round(box_w * scale))
    bl = int(round(box_l * scale))

    cache: Dict[Tuple[int, int, int], List[List[Tuple[int, int, int, int]]]] = {}

    cut_steps = sorted({bw, bl})

    def cut_positions(total: int) -> List[int]:
        positions = set()
        min_step = min(cut_steps) if cut_steps else 0
        for step in cut_steps:
            if step <= 0:
                continue
            pos = step
            while pos < total - min_step:
                positions.add(pos)
                pos += step
        return sorted(positions)

    def pack(rect_w: int, rect_l: int, depth: int) -> List[List[Tuple[int, int, int, int]]]:
        key = (rect_w, rect_l, depth)
        if key in cache:
            return cache[key]

        layouts: List[List[Tuple[int, int, int, int]]] = []

        grid_a = _grid_layout_int(rect_w, rect_l, bw, bl)
        if grid_a:
            layouts.append(grid_a)

        if bw != bl:
            grid_b = _grid_layout_int(rect_w, rect_l, bl, bw)
            if grid_b:
                layouts.append(grid_b)

        if depth > 0:
            for cut in cut_positions(rect_w):
                left = pack(cut, rect_l, depth - 1)[:per_split_limit]
                right = pack(rect_w - cut, rect_l, depth - 1)[:per_split_limit]
                for left_layout in left:
                    for right_layout in right:
                        combined = list(left_layout)
                        combined.extend(
                            (x + cut, y, w, lgt) for x, y, w, lgt in right_layout
                        )
                        layouts.append(combined)

            for cut in cut_positions(rect_l):
                bottom = pack(rect_w, cut, depth - 1)[:per_split_limit]
                top = pack(rect_w, rect_l - cut, depth - 1)[:per_split_limit]
                for b in bottom:
                    for t in top:
                        combined = list(b)
                        combined.extend((x, y + cut, w, lgt) for x, y, w, lgt in t)
                        layouts.append(combined)

        ranked: List[Tuple[Tuple[int, int], List[Tuple[int, int, int, int]]]] = []
        seen = set()
        for layout in layouts:
            signature = tuple(sorted(layout))
            if signature in seen:
                continue
            seen.add(signature)
            ranked.append((_layout_score(layout), layout))

        ranked.sort(key=lambda item: (item[0][0], item[0][1], item[1]), reverse=True)
        cache[key] = [layout for _, layout in ranked[:max_variants]]
        return cache[key]

    int_layouts = pack(pw, pl, max_depth)
    layouts: List[LayerLayout] = []
    seen = set()
    for layout in int_layouts:
        float_layout = [
            (x / scale, y / scale, w / scale, length / scale)
            for x, y, w, length in layout
        ]
        signature = layout_signature(float_layout)
        if signature in seen:
            continue
        seen.add(signature)
        layouts.append(float_layout)
        if len(layouts) >= max_variants:
            break

    return layouts
