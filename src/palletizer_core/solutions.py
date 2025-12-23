from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Iterable, Literal

LayerLayout = list[tuple[float, float, float, float]]

SolutionKind = Literal["standard", "extra"]

STANDARD_ORDER = [
    "dynamic",
    "mixed",
    "column_wxl",
    "column_lxw",
    "pinwheel",
    "interlock",
    "row_by_row",
]

DISPLAY_MAP = {
    "dynamic": "Dynamic",
    "mixed": "Mixed",
    "column_wxl": "Column (W x L)",
    "column_lxw": "Column (L x W)",
    "pinwheel": "Pinwheel",
    "interlock": "Interlock",
    "row_by_row": "Row by row",
}

STANDARD_KEY_ALIASES = {
    "column": "column_wxl",
    "column_rotated": "column_lxw",
}


@dataclass(frozen=True)
class Solution:
    key: str
    display: str
    kind: SolutionKind
    layout: LayerLayout
    metrics: dict[str, float]
    signature: tuple


@dataclass
class SolutionCatalog:
    solutions: list[Solution]
    by_key: dict[str, Solution]
    standard_order: list[str] = field(default_factory=lambda: list(STANDARD_ORDER))

    @classmethod
    def empty(cls) -> "SolutionCatalog":
        return cls(solutions=[], by_key={}, standard_order=list(STANDARD_ORDER))

    def displays(self) -> list[str]:
        return [solution.display for solution in self.solutions]

    def key_by_display(self) -> dict[str, str]:
        return {solution.display: solution.key for solution in self.solutions}


def normalize_pattern_key(name: str) -> str:
    return STANDARD_KEY_ALIASES.get(name, name)


def display_for_key(key: str) -> str:
    if key in DISPLAY_MAP:
        return DISPLAY_MAP[key]
    return key.replace("_", " ").replace("-", " ").title()


def _solution_metrics_value(solution: Solution, metric: str) -> float:
    return float(solution.metrics.get(metric, 0.0))


def _dedupe_sort_key(solution: Solution, standard_order: dict[str, int]) -> tuple:
    kind_priority = 0 if solution.kind == "standard" else 1
    cartons = _solution_metrics_value(solution, "cartons")
    stability = _solution_metrics_value(solution, "stability")
    if solution.kind == "standard":
        tie_break = standard_order.get(solution.key, len(standard_order))
    else:
        tie_break = solution.key
    return (kind_priority, -cartons, -stability, tie_break)


def _ranking_sort_key(solution: Solution, standard_order: dict[str, int]) -> tuple:
    cartons = _solution_metrics_value(solution, "cartons")
    stability = _solution_metrics_value(solution, "stability")
    kind_priority = 0 if solution.kind == "standard" else 1
    if solution.kind == "standard":
        tie_break = standard_order.get(solution.key, len(standard_order))
    else:
        tie_break = solution.key
    return (-cartons, -stability, kind_priority, tie_break)


def _ensure_unique_displays(solutions: list[Solution]) -> list[Solution]:
    counts: dict[str, int] = {}
    for solution in solutions:
        counts[solution.display] = counts.get(solution.display, 0) + 1
    if all(count == 1 for count in counts.values()):
        return solutions
    unique: list[Solution] = []
    for solution in solutions:
        if counts.get(solution.display, 0) > 1:
            unique.append(replace(solution, display=f"{solution.display} ({solution.key})"))
        else:
            unique.append(solution)
    return unique


def build_solution_catalog(
    candidates: Iterable[Solution],
    *,
    standard_order: Iterable[str] = STANDARD_ORDER,
) -> SolutionCatalog:
    order_list = list(standard_order)
    order_index = {key: idx for idx, key in enumerate(order_list)}
    signature_groups: dict[tuple, list[Solution]] = {}
    for solution in candidates:
        signature_groups.setdefault(solution.signature, []).append(solution)

    winners: list[Solution] = []
    for group in signature_groups.values():
        winner = sorted(group, key=lambda sol: _dedupe_sort_key(sol, order_index))[0]
        winners.append(winner)

    winners_sorted = sorted(winners, key=lambda sol: _ranking_sort_key(sol, order_index))
    winners_sorted = _ensure_unique_displays(winners_sorted)
    by_key = {solution.key: solution for solution in winners_sorted}
    return SolutionCatalog(
        solutions=winners_sorted,
        by_key=by_key,
        standard_order=order_list,
    )


def ui_model_from_catalog(catalog: SolutionCatalog) -> tuple[list[str], list[str]]:
    dropdown_options = catalog.displays()
    table_rows = [solution.key for solution in catalog.solutions]
    return dropdown_options, table_rows
