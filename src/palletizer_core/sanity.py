from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .models import Carton, Pallet

LayerLayout = List[Tuple[float, float, float, float]]


@dataclass(frozen=True)
class SanityPolicy:
    min_stack_height_boxes: int = 2
    min_column_count: int = 3
    single_column_ratio: float = 0.6
    min_row_count: int = 3
    single_row_ratio: float = 0.6
    max_islands: int = 2
    min_area_ratio: float = 0.6
    eps: float = 1e-6
    touch_eps: float = 1e-6


DEFAULT_SANITY_POLICY = SanityPolicy()


def layout_columns_x(layout: LayerLayout, eps: float = 1e-6) -> Dict[float, LayerLayout]:
    columns: Dict[float, LayerLayout] = {}
    for rect in layout:
        x, _, _, _ = rect
        key = round(x / eps) * eps
        columns.setdefault(key, []).append(rect)
    return columns


def layout_rows_y(layout: LayerLayout, eps: float = 1e-6) -> Dict[float, LayerLayout]:
    rows: Dict[float, LayerLayout] = {}
    for rect in layout:
        _, y, _, _ = rect
        key = round(y / eps) * eps
        rows.setdefault(key, []).append(rect)
    return rows


def is_single_carton_column(
    layout: LayerLayout,
    min_stack_height_boxes: int = 2,
    eps: float = 1e-6,
) -> bool:
    if not layout:
        return False
    columns = layout_columns_x(layout, eps=eps)
    if len(columns) < 2:
        return False
    counts = [len(col) for col in columns.values()]
    single_cols = sum(1 for c in counts if c < min_stack_height_boxes)
    return single_cols / max(len(counts), 1) >= 0.6


def is_single_carton_row(
    layout: LayerLayout,
    min_stack_width_boxes: int = 2,
    eps: float = 1e-6,
) -> bool:
    if not layout:
        return False
    rows = layout_rows_y(layout, eps=eps)
    if len(rows) < 2:
        return False
    counts = [len(row) for row in rows.values()]
    single_rows = sum(1 for c in counts if c < min_stack_width_boxes)
    return single_rows / max(len(counts), 1) >= 0.6


def _touches(
    a: Tuple[float, float, float, float],
    b: Tuple[float, float, float, float],
    eps: float,
) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (
        ax + aw < bx - eps
        or bx + bw < ax - eps
        or ay + ah < by - eps
        or by + bh < ay - eps
    )


def connected_components(layout: LayerLayout, touch_eps: float = 1e-6) -> int:
    if not layout:
        return 0
    visited = set()
    components = 0
    for i in range(len(layout)):
        if i in visited:
            continue
        components += 1
        stack = [i]
        visited.add(i)
        while stack:
            idx = stack.pop()
            for j in range(len(layout)):
                if j in visited:
                    continue
                if _touches(layout[idx], layout[j], touch_eps):
                    visited.add(j)
                    stack.append(j)
    return components


def sanity_flags(
    layout: LayerLayout,
    carton: Carton,
    pallet: Pallet,
    policy: SanityPolicy | None = None,
) -> set[str]:
    if policy is None:
        policy = DEFAULT_SANITY_POLICY
    flags: set[str] = set()

    columns = layout_columns_x(layout, eps=policy.eps)
    if len(columns) >= policy.min_column_count and is_single_carton_column(
        layout,
        min_stack_height_boxes=policy.min_stack_height_boxes,
        eps=policy.eps,
    ):
        flags.add("single_carton_column")

    rows = layout_rows_y(layout, eps=policy.eps)
    if len(rows) >= policy.min_row_count and is_single_carton_row(
        layout,
        min_stack_width_boxes=policy.min_stack_height_boxes,
        eps=policy.eps,
    ):
        flags.add("single_carton_row")

    islands = connected_components(layout, touch_eps=policy.touch_eps)
    if islands > policy.max_islands:
        flags.add("disconnected_islands")

    return flags


def is_sane(
    layout: LayerLayout,
    carton: Carton,
    pallet: Pallet,
    policy: SanityPolicy | None = None,
) -> bool:
    if not layout:
        return True
    return not sanity_flags(layout, carton, pallet, policy)
