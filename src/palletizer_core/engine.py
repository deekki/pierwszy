from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from .models import Carton, Pallet
from .sanity import DEFAULT_SANITY_POLICY, connected_components, is_sane
from .signature import layout_signature
from .solutions import (
    STANDARD_KEYS_ORDER,
    Solution,
    SolutionCatalog,
    build_solution_catalog,
    display_for_key,
    normalize_pattern_key,
)
from .units import MM
from .selector import PatternScore, PatternSelector
from .sequencer import EvenOddSequencer

LayerLayout = List[Tuple[float, float, float, float]]


def apply_spacing(pattern: LayerLayout, spacing: float) -> LayerLayout:
    """Center boxes within spaced slots."""
    adjusted = []
    for x, y, w, h in pattern:
        new_w = w - spacing
        new_h = h - spacing
        adjusted.append((x + spacing / 2, y + spacing / 2, new_w, new_h))
    return adjusted


@dataclass
class PalletInputs:
    pallet_w: MM
    pallet_l: MM
    pallet_h: MM
    box_w: MM
    box_l: MM
    box_h: MM
    thickness: MM
    spacing: MM
    slip_count: int
    num_layers: int
    max_stack: MM
    include_pallet_height: bool

    @property
    def box_w_ext(self) -> float:
        return self.box_w + 2 * self.thickness

    @property
    def box_l_ext(self) -> float:
        return self.box_l + 2 * self.thickness


@dataclass
class LayoutComputation:
    layouts: List[Tuple[int, LayerLayout, str]]
    layout_map: Dict[str, int]
    best_layout_name: str
    best_even: LayerLayout
    best_odd: LayerLayout
    best_layout_key: str = ""
    best_count_layout_name: str = ""
    solution_catalog: SolutionCatalog = field(default_factory=SolutionCatalog.empty)
    scores: Dict[str, PatternScore] = field(default_factory=dict)
    display_map: Dict[str, str] = field(default_factory=dict)
    row_by_row_vertical: int = 0
    row_by_row_horizontal: int = 0
    raw_layout_entries: List[Tuple[int, LayerLayout, str]] = field(default_factory=list)
    filtered_layout_entries: List[Tuple[int, LayerLayout, str]] = field(default_factory=list)


def group_cartons(positions: LayerLayout) -> List[LayerLayout]:
    """Group cartons that touch or overlap using AABB collision detection."""

    def collide(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> bool:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)

    groups = []
    used = set()
    for i in range(len(positions)):
        if i in used:
            continue
        stack = [i]
        used.add(i)
        current_group = []
        while stack:
            idx = stack.pop()
            current_group.append(positions[idx])
            for j in range(len(positions)):
                if j in used:
                    continue
                if collide(positions[idx], positions[j]):
                    used.add(j)
                    stack.append(j)
        groups.append(current_group)
    return groups


def center_layout(
    positions: LayerLayout,
    pallet_w: float,
    pallet_l: float,
    center_enabled: bool,
    center_mode: str,
) -> LayerLayout:
    if not positions or not center_enabled:
        return positions
    if center_mode == "Cała warstwa":
        x_min = min(x for x, y, w, h in positions)
        x_max = max(x + w for x, y, w, h in positions)
        y_min = min(y for x, y, w, h in positions)
        y_max = max(y + h for x, y, w, h in positions)
        offset_x = (pallet_w - (x_max - x_min)) / 2 - x_min
        offset_y = (pallet_l - (y_max - y_min)) / 2 - y_min
        return [(x + offset_x, y + offset_y, w, h) for x, y, w, h in positions]

    groups = group_cartons(positions)
    centered_positions: LayerLayout = []
    for group in groups:
        x_min = min(x for x, y, w, h in group)
        x_max = max(x + w for x, y, w, h in group)
        y_min = min(y for x, y, w, h in group)
        y_max = max(y + h for x, y, w, h in group)
        offset_x = (pallet_w - (x_max - x_min)) / 2 - x_min
        offset_y = (pallet_l - (y_max - y_min)) / 2 - y_min
        centered_positions.extend(
            [(x + offset_x, y + offset_y, w, h) for x, y, w, h in group]
        )

    # If centering individual groups makes them collide, fall back to
    # centering the entire layer instead of merging the groups.
    if len(group_cartons(centered_positions)) != len(groups):
        x_min = min(x for x, y, w, h in positions)
        x_max = max(x + w for x, y, w, h in positions)
        y_min = min(y for x, y, w, h in positions)
        y_max = max(y + h for x, y, w, h in positions)
        offset_x = (pallet_w - (x_max - x_min)) / 2 - x_min
        offset_y = (pallet_l - (y_max - y_min)) / 2 - y_min
        return [(x + offset_x, y + offset_y, w, h) for x, y, w, h in positions]
    return centered_positions


def count_row_by_row_rows(
    carton: Carton, pattern: LayerLayout | None
) -> Tuple[int, int]:
    if not pattern:
        return 0, 0

    vertical_rows: List[float] = []
    horizontal_rows: List[float] = []
    tol = 1e-6
    width = carton.width
    length = carton.length

    for _, y, w, h in pattern:
        if math.isclose(w, width, rel_tol=1e-6, abs_tol=1e-6) and math.isclose(
            h, length, rel_tol=1e-6, abs_tol=1e-6
        ):
            target = vertical_rows
        elif math.isclose(w, length, rel_tol=1e-6, abs_tol=1e-6) and math.isclose(
            h, width, rel_tol=1e-6, abs_tol=1e-6
        ):
            target = horizontal_rows
        else:
            target = vertical_rows if w >= h else horizontal_rows

        if not any(math.isclose(y, existing, rel_tol=1e-6, abs_tol=tol) for existing in target):
            target.append(y)

    return len(vertical_rows), len(horizontal_rows)


def build_row_by_row_pattern(
    carton: Carton, pallet: Pallet, vertical: int, horizontal: int
) -> LayerLayout:
    pattern: LayerLayout = []
    vertical_remaining = max(vertical, 0)
    horizontal_remaining = max(horizontal, 0)
    y = 0.0
    tol = 1e-6
    orientation = "vertical" if vertical_remaining > 0 else "horizontal"

    while y + tol < pallet.length and (
        vertical_remaining > 0 or horizontal_remaining > 0
    ):
        if orientation == "vertical":
            if vertical_remaining <= 0:
                orientation = "horizontal"
                continue
            row_height = carton.length
            col_width = carton.width
            if row_height <= 0 or col_width <= 0 or y + row_height - tol > pallet.length:
                break
            n_cols = int(pallet.width // col_width) if col_width > 0 else 0
            if n_cols == 0:
                vertical_remaining = 0
                orientation = "horizontal"
                continue
            for c in range(n_cols):
                pattern.append((c * col_width, y, col_width, row_height))
            y += row_height
            vertical_remaining -= 1
        else:
            if horizontal_remaining <= 0:
                orientation = "vertical"
                continue
            row_height = carton.width
            col_width = carton.length
            if row_height <= 0 or col_width <= 0 or y + row_height - tol > pallet.length:
                break
            n_cols = int(pallet.width // col_width) if col_width > 0 else 0
            if n_cols == 0:
                horizontal_remaining = 0
                orientation = "vertical"
                continue
            for c in range(n_cols):
                pattern.append((c * col_width, y, col_width, row_height))
            y += row_height
            horizontal_remaining -= 1

        if vertical_remaining <= 0 and horizontal_remaining <= 0:
            break
        if orientation == "vertical":
            orientation = "horizontal" if horizontal_remaining > 0 else "vertical"
        else:
            orientation = "vertical" if vertical_remaining > 0 else "horizontal"

    return pattern


def normalize_row_by_row_counts(
    carton: Carton,
    pallet: Pallet,
    vertical: int,
    horizontal: int,
    axis_changed: str | None = None,
) -> Tuple[int, int]:
    vertical = max(int(vertical), 0)
    horizontal = max(int(horizontal), 0)

    row_height_vertical = carton.length
    row_height_horizontal = carton.width
    available_height = pallet.length

    max_vertical_total = (
        int(available_height // row_height_vertical) if row_height_vertical > 0 else 0
    )
    max_horizontal_total = (
        int(available_height // row_height_horizontal)
        if row_height_horizontal > 0
        else 0
    )

    vertical_cols = int(pallet.width // carton.width) if carton.width > 0 else 0
    horizontal_cols = int(pallet.width // carton.length) if carton.length > 0 else 0

    if vertical_cols == 0:
        vertical = 0
    else:
        vertical = min(vertical, max_vertical_total)
    if horizontal_cols == 0:
        horizontal = 0
    else:
        horizontal = min(horizontal, max_horizontal_total)

    if axis_changed == "vertical":
        remaining = available_height - vertical * row_height_vertical
        remaining = max(remaining, 0)
        max_horizontal = (
            int(remaining // row_height_horizontal)
            if row_height_horizontal > 0
            else 0
        )
        horizontal = min(horizontal, max_horizontal)
    elif axis_changed == "horizontal":
        remaining = available_height - horizontal * row_height_horizontal
        remaining = max(remaining, 0)
        max_vertical = (
            int(remaining // row_height_vertical) if row_height_vertical > 0 else 0
        )
        vertical = min(vertical, max_vertical)
    else:
        while (
            vertical * row_height_vertical + horizontal * row_height_horizontal
            > available_height
            and (vertical > 0 or horizontal > 0)
        ):
            if vertical * row_height_vertical >= horizontal * row_height_horizontal:
                if vertical > 0:
                    vertical -= 1
                elif horizontal > 0:
                    horizontal -= 1
            elif horizontal > 0:
                horizontal -= 1
            else:
                break

    return max(vertical, 0), max(horizontal, 0)


def build_layouts(
    inputs: PalletInputs,
    maximize_mixed: bool,
    center_enabled: bool,
    center_mode: str,
    shift_even: bool,
    row_by_row_customizer: Optional[
        Callable[[Carton, Pallet, LayerLayout | None], tuple[LayerLayout | None, int, int]]
    ] = None,
    *,
    extended_library: bool = False,
    dynamic_variants: bool = False,
    deep_search: bool = False,
    filter_sanity: bool = False,
    result_limit: int | None = None,
    allow_offsets: bool = False,
    min_support: float = 0.80,
    assume_full_support: bool = False,
) -> LayoutComputation:
    pallet = Pallet(inputs.pallet_w, inputs.pallet_l, inputs.pallet_h)
    calc_carton = Carton(
        inputs.box_w_ext + inputs.spacing,
        inputs.box_l_ext + inputs.spacing,
        inputs.box_h,
    )
    selector = PatternSelector(calc_carton, pallet)
    patterns = selector.generate_all(
        maximize_mixed=maximize_mixed,
        extended_library=extended_library,
        dynamic_variants=dynamic_variants or extended_library,
        deep_search=deep_search,
    )

    row_by_row_vertical = 0
    row_by_row_horizontal = 0
    if "row_by_row" in patterns:
        if row_by_row_customizer is not None:
            custom_pattern, row_by_row_vertical, row_by_row_horizontal = (
                row_by_row_customizer(calc_carton, pallet, patterns.get("row_by_row"))
            )
            patterns["row_by_row"] = custom_pattern if custom_pattern is not None else []
        else:
            row_by_row_vertical, row_by_row_horizontal = count_row_by_row_rows(
                calc_carton, patterns.get("row_by_row")
            )
    else:
        row_by_row_vertical = 0
        row_by_row_horizontal = 0

    scores: Dict[str, PatternScore] = {}
    display_map: Dict[str, str] = {}
    entries: List[Dict[str, object]] = []

    for name, pattern in patterns.items():
        score = selector.score(pattern)
        score.name = name
        key = normalize_pattern_key(name)
        display = display_for_key(key)
        score.display_name = display
        scores[key] = score
        display_map[key] = display

    for name, pattern in patterns.items():
        key = normalize_pattern_key(name)
        display = display_for_key(key)
        kind = "standard" if key in STANDARD_KEYS_ORDER else "extra"
        adjusted = apply_spacing(pattern, inputs.spacing)
        centered = center_layout(
            adjusted, inputs.pallet_w, inputs.pallet_l, center_enabled, center_mode
        )
        score = scores[key]
        weakest_carton = score.weakest_carton or (0.0, 0.0, 0.0, 0.0)
        area_ratio = (
            sum(w * length for _, _, w, length in centered)
            / (inputs.pallet_w * inputs.pallet_l)
            if inputs.pallet_w > 0 and inputs.pallet_l > 0
            else 0.0
        )
        islands = connected_components(centered, touch_eps=DEFAULT_SANITY_POLICY.touch_eps)
        signature = layout_signature(centered)
        metrics = {
            "cartons": float(len(centered)),
            "stability": float(score.stability),
            "layer_eff": float(score.layer_eff),
            "cube_eff": float(score.cube_eff),
            "support_fraction": float(score.support_fraction),
            "min_support": float(score.min_support),
            "edge_contact": float(score.edge_contact),
            "min_edge_clearance": float(score.min_edge_clearance),
            "grip_changes": float(score.grip_changes),
            "orientation_mix": float(score.orientation_mix),
            "com_offset": float(score.com_offset),
            "instability_risk": 1.0 if score.instability_risk else 0.0,
            "weakest_support": float(score.weakest_support),
            "weakest_carton_x": float(weakest_carton[0]),
            "weakest_carton_y": float(weakest_carton[1]),
        }
        entries.append(
            {
                "name": name,
                "key": key,
                "kind": kind,
                "pattern": pattern,
                "layout": centered,
                "display": display,
                "count": len(centered),
                "score": score,
                "area_ratio": area_ratio,
                "islands": islands,
                "signature": signature,
                "metrics": metrics,
            }
        )

    raw_layout_entries = [
        (entry["count"], entry["layout"], entry["display"]) for entry in entries
    ]

    def _entry_metric(entry: Dict[str, object]) -> Tuple[float, ...]:
        score = entry["score"]
        return (
            float(entry["count"]),
            float(entry["area_ratio"]),
            float(score.support_fraction),
            float(score.min_support),
            -float(score.com_offset),
            float(score.min_edge_clearance),
            -float(entry["islands"]),
            entry["signature"],
            str(entry["display"]),
        )

    best_raw_entry = None
    if entries:
        best_raw_entry = max(entries, key=_entry_metric)

    filtered_entries = list(entries)
    if filter_sanity:
        filtered_entries = [
            entry
            for entry in filtered_entries
            if is_sane(entry["layout"], calc_carton, pallet, DEFAULT_SANITY_POLICY)
        ]
        if filtered_entries:
            best_area = max(entry["area_ratio"] for entry in filtered_entries)
            min_area = DEFAULT_SANITY_POLICY.min_area_ratio
            if best_area >= min_area:
                filtered_entries = [
                    entry
                    for entry in filtered_entries
                    if entry["area_ratio"] >= min_area
                ]
        if not filtered_entries and best_raw_entry is not None:
            filtered_entries = [best_raw_entry]

    candidates = [
        Solution(
            key=entry["key"],
            display=entry["display"],
            kind=entry["kind"],
            layout=entry["layout"],
            metrics=entry["metrics"],
            signature=entry["signature"],
        )
        for entry in filtered_entries
    ]
    solution_catalog = build_solution_catalog(candidates)
    if result_limit is not None and result_limit > 0:
        solution_catalog = SolutionCatalog(
            solutions=solution_catalog.solutions[:result_limit],
            by_key={
                solution.key: solution
                for solution in solution_catalog.solutions[:result_limit]
            },
            standard_keys_order=solution_catalog.standard_keys_order,
        )
    filtered_entries = [
        entry
        for entry in filtered_entries
        if entry["key"] in solution_catalog.by_key
    ]
    best_entry = None
    best_solution = solution_catalog.solutions[0] if solution_catalog.solutions else None
    if best_solution:
        for entry in filtered_entries:
            if entry["key"] == best_solution.key:
                best_entry = entry
                break
    if best_entry is None and best_raw_entry is not None:
        best_entry = best_raw_entry

    best_key = best_entry["key"] if best_entry else ""
    best_pattern: LayerLayout = best_entry["pattern"] if best_entry else []

    seq = EvenOddSequencer(
        best_pattern,
        calc_carton,
        pallet,
        allow_offsets=allow_offsets,
        min_support=min_support,
        assume_full_support=assume_full_support,
    )
    even_base, odd_shifted = seq.best_shift()
    even_centered = center_layout(
        even_base, inputs.pallet_w, inputs.pallet_l, center_enabled, center_mode
    )
    odd_centered = center_layout(
        odd_shifted, inputs.pallet_w, inputs.pallet_l, center_enabled, center_mode
    )
    if shift_even:
        best_even = apply_spacing(odd_centered, inputs.spacing)
        best_odd = apply_spacing(even_centered, inputs.spacing)
    else:
        best_even = apply_spacing(even_centered, inputs.spacing)
        best_odd = apply_spacing(odd_centered, inputs.spacing)

    layout_entries = [
        (int(solution.metrics.get("cartons", 0)), solution.layout, solution.display)
        for solution in solution_catalog.solutions
    ]
    layout_map = {name: idx for idx, (_, __, name) in enumerate(layout_entries)}
    best_layout_name = display_for_key(best_key) if best_key else ""
    best_count_layout_name = best_layout_name

    return LayoutComputation(
        layouts=layout_entries,
        layout_map=layout_map,
        best_layout_name=best_layout_name,
        best_even=best_even,
        best_odd=best_odd,
        best_layout_key=best_key,
        best_count_layout_name=best_count_layout_name,
        solution_catalog=solution_catalog,
        scores=scores,
        display_map=display_map,
        row_by_row_vertical=row_by_row_vertical,
        row_by_row_horizontal=row_by_row_horizontal,
        raw_layout_entries=raw_layout_entries,
        filtered_layout_entries=layout_entries,
    )
