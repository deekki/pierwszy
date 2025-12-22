from __future__ import annotations

from typing import Dict, List, Tuple

from palletizer_core import algorithms
from .models import Carton, Pallet

LayerLayout = List[Tuple[float, float, float, float]]

MAX_VARIANTS = 10


def _fill_block(
    x0: float,
    y0: float,
    block_w: float,
    block_l: float,
    box_w: float,
    box_l: float,
) -> LayerLayout:
    cols = int(block_w // box_w) if box_w > 0 else 0
    rows = int(block_l // box_l) if box_l > 0 else 0
    if cols <= 0 or rows <= 0:
        return []
    pattern: LayerLayout = []
    for r in range(rows):
        for c in range(cols):
            pattern.append((x0 + c * box_w, y0 + r * box_l, box_w, box_l))
    return pattern


def _fill_interlock(
    x0: float,
    y0: float,
    block_w: float,
    block_l: float,
    box_w: float,
    box_l: float,
) -> LayerLayout:
    try:
        _, _, layers = algorithms.compute_interlocked_layout(
            block_w, block_l, box_w, box_l, num_layers=1
        )
    except Exception:
        return []
    if not layers:
        return []
    return [(x + x0, y + y0, w, l) for x, y, w, l in layers[0]]


def generate_block2(carton: Carton, pallet: Pallet) -> Dict[str, LayerLayout]:
    patterns: Dict[str, LayerLayout] = {}
    box_w, box_l = carton.width, carton.length
    pallet_w, pallet_l = pallet.width, pallet.length
    max_cols_a = int(pallet_w // box_w) if box_w > 0 else 0
    max_rows_a = int(pallet_l // box_l) if box_l > 0 else 0

    # Split along X
    for split_cols in range(1, max_cols_a):
        if len(patterns) >= MAX_VARIANTS:
            break
        left_w = split_cols * box_w
        right_w = pallet_w - left_w
        if right_w < box_l:
            continue
        left = _fill_block(0.0, 0.0, left_w, pallet_l, box_w, box_l)
        right = _fill_block(left_w, 0.0, right_w, pallet_l, box_l, box_w)
        if left and right:
            patterns[f"block2_x_split_{split_cols}"] = left + right
            if len(patterns) >= MAX_VARIANTS:
                break
            patterns[f"block2_x_split_{split_cols}_swap"] = (
                _fill_block(0.0, 0.0, left_w, pallet_l, box_l, box_w)
                + _fill_block(left_w, 0.0, right_w, pallet_l, box_w, box_l)
            )

    # Split along Y
    for split_rows in range(1, max_rows_a):
        if len(patterns) >= MAX_VARIANTS:
            break
        bottom_l = split_rows * box_l
        top_l = pallet_l - bottom_l
        if top_l < box_w:
            continue
        bottom = _fill_block(0.0, 0.0, pallet_w, bottom_l, box_w, box_l)
        top = _fill_block(0.0, bottom_l, pallet_w, top_l, box_l, box_w)
        if bottom and top:
            patterns[f"block2_y_split_{split_rows}"] = bottom + top
            if len(patterns) >= MAX_VARIANTS:
                break
            patterns[f"block2_y_split_{split_rows}_swap"] = (
                _fill_block(0.0, 0.0, pallet_w, bottom_l, box_l, box_w)
                + _fill_block(0.0, bottom_l, pallet_w, top_l, box_w, box_l)
            )

    return patterns


def generate_block3(carton: Carton, pallet: Pallet) -> Dict[str, LayerLayout]:
    patterns: Dict[str, LayerLayout] = {}
    box_w, box_l = carton.width, carton.length
    pallet_w, pallet_l = pallet.width, pallet.length
    max_cols_a = int(pallet_w // box_w) if box_w > 0 else 0
    max_rows_a = int(pallet_l // box_l) if box_l > 0 else 0

    sequences = [
        ("A", "B", "A"),
        ("B", "A", "B"),
    ]

    for split_cols in range(1, max_cols_a - 1):
        for mid_cols in range(1, max_cols_a - split_cols):
            if len(patterns) >= MAX_VARIANTS:
                break
            left_w = split_cols * box_w
            mid_w = mid_cols * box_w
            right_w = pallet_w - left_w - mid_w
            if right_w <= 0:
                continue
            for seq in sequences:
                blocks = []
                x0 = 0.0
                widths = [left_w, mid_w, right_w]
                for block_w, orient in zip(widths, seq, strict=True):
                    if orient == "A":
                        block = _fill_block(x0, 0.0, block_w, pallet_l, box_w, box_l)
                    else:
                        block = _fill_block(x0, 0.0, block_w, pallet_l, box_l, box_w)
                    if not block:
                        blocks = []
                        break
                    blocks.extend(block)
                    x0 += block_w
                if blocks:
                    key = f"block3_x_splits_{split_cols}_{mid_cols}_{''.join(seq)}"
                    patterns[key] = blocks
                    if len(patterns) >= MAX_VARIANTS:
                        break
        if len(patterns) >= MAX_VARIANTS:
            break

    for split_rows in range(1, max_rows_a - 1):
        for mid_rows in range(1, max_rows_a - split_rows):
            if len(patterns) >= MAX_VARIANTS:
                break
            bottom_l = split_rows * box_l
            mid_l = mid_rows * box_l
            top_l = pallet_l - bottom_l - mid_l
            if top_l <= 0:
                continue
            for seq in sequences:
                blocks = []
                y0 = 0.0
                lengths = [bottom_l, mid_l, top_l]
                for block_l, orient in zip(lengths, seq, strict=True):
                    if orient == "A":
                        block = _fill_block(0.0, y0, pallet_w, block_l, box_w, box_l)
                    else:
                        block = _fill_block(0.0, y0, pallet_w, block_l, box_l, box_w)
                    if not block:
                        blocks = []
                        break
                    blocks.extend(block)
                    y0 += block_l
                if blocks:
                    key = f"block3_y_splits_{split_rows}_{mid_rows}_{''.join(seq)}"
                    patterns[key] = blocks
                    if len(patterns) >= MAX_VARIANTS:
                        break
        if len(patterns) >= MAX_VARIANTS:
            break

    return patterns


def generate_block4(carton: Carton, pallet: Pallet) -> Dict[str, LayerLayout]:
    patterns: Dict[str, LayerLayout] = {}
    box_w, box_l = carton.width, carton.length
    pallet_w, pallet_l = pallet.width, pallet.length
    max_cols_a = int(pallet_w // box_w) if box_w > 0 else 0
    max_rows_a = int(pallet_l // box_l) if box_l > 0 else 0

    variants = {
        "checker": [["A", "B"], ["B", "A"]],
        "pinwheel": [["A", "B"], ["A", "B"]],
    }

    for split_cols in range(1, max_cols_a):
        for split_rows in range(1, max_rows_a):
            if len(patterns) >= MAX_VARIANTS:
                break
            left_w = split_cols * box_w
            right_w = pallet_w - left_w
            bottom_l = split_rows * box_l
            top_l = pallet_l - bottom_l
            if right_w <= 0 or top_l <= 0:
                continue
            for name, grid in variants.items():
                blocks: LayerLayout = []
                coords = [
                    (0.0, 0.0, left_w, bottom_l, grid[0][0]),
                    (left_w, 0.0, right_w, bottom_l, grid[0][1]),
                    (0.0, bottom_l, left_w, top_l, grid[1][0]),
                    (left_w, bottom_l, right_w, top_l, grid[1][1]),
                ]
                for x0, y0, bw, bl, orient in coords:
                    if orient == "A":
                        block = _fill_block(x0, y0, bw, bl, box_w, box_l)
                    else:
                        block = _fill_block(x0, y0, bw, bl, box_l, box_w)
                    if not block:
                        blocks = []
                        break
                    blocks.extend(block)
                if blocks:
                    patterns[f"block4_{name}_split_{split_cols}_{split_rows}"] = blocks
                    if len(patterns) >= MAX_VARIANTS:
                        break
        if len(patterns) >= MAX_VARIANTS:
            break

    return patterns


def generate_hybrid(carton: Carton, pallet: Pallet) -> Dict[str, LayerLayout]:
    patterns: Dict[str, LayerLayout] = {}
    box_w, box_l = carton.width, carton.length
    pallet_w, pallet_l = pallet.width, pallet.length

    ratios = [0.6, 0.7]
    for ratio in ratios:
        if len(patterns) >= MAX_VARIANTS:
            break
        split_w = pallet_w * ratio
        split_cols = int(split_w // box_w) if box_w > 0 else 0
        left_w = split_cols * box_w
        right_w = pallet_w - left_w
        if left_w > 0 and right_w > 0:
            left = _fill_block(0.0, 0.0, left_w, pallet_l, box_w, box_l)
            right = _fill_interlock(left_w, 0.0, right_w, pallet_l, box_w, box_l)
            if left and right:
                patterns[f"hybrid_x_{int(ratio*100)}_col_interlock"] = left + right
            if len(patterns) >= MAX_VARIANTS:
                break
            left_i = _fill_interlock(0.0, 0.0, left_w, pallet_l, box_w, box_l)
            right_c = _fill_block(left_w, 0.0, right_w, pallet_l, box_w, box_l)
            if left_i and right_c:
                patterns[f"hybrid_x_{int(ratio*100)}_interlock_col"] = left_i + right_c

        split_l = pallet_l * ratio
        split_rows = int(split_l // box_l) if box_l > 0 else 0
        bottom_l = split_rows * box_l
        top_l = pallet_l - bottom_l
        if bottom_l > 0 and top_l > 0:
            bottom = _fill_block(0.0, 0.0, pallet_w, bottom_l, box_w, box_l)
            top = _fill_interlock(0.0, bottom_l, pallet_w, top_l, box_w, box_l)
            if bottom and top:
                patterns[f"hybrid_y_{int(ratio*100)}_col_interlock"] = bottom + top
            if len(patterns) >= MAX_VARIANTS:
                break
            bottom_i = _fill_interlock(0.0, 0.0, pallet_w, bottom_l, box_w, box_l)
            top_c = _fill_block(0.0, bottom_l, pallet_w, top_l, box_w, box_l)
            if bottom_i and top_c:
                patterns[f"hybrid_y_{int(ratio*100)}_interlock_col"] = bottom_i + top_c

    return patterns
