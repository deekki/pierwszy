from __future__ import annotations

from palletizer_core.engine import LayoutComputation, PalletInputs


def apply_layout_result_to_tab_state(
    tab,
    inputs: PalletInputs,
    result: LayoutComputation,
    *,
    force_layers: bool = False,
) -> None:
    tab.layouts = result.layouts
    tab.layout_map = result.layout_map
    tab.best_layout_name = result.best_count_layout_name or result.best_layout_name
    tab.best_layout_key = result.best_layout_key
    tab.solution_catalog = result.solution_catalog
    tab.solution_by_key = result.solution_catalog.by_key
    tab.best_even = result.best_even
    tab.best_odd = result.best_odd
    tab.update_transform_frame()
    tab.num_layers = inputs.num_layers
    tab.slip_count = inputs.slip_count
    update_layers = getattr(tab, "update_layers", None)
    if callable(update_layers):
        try:
            update_layers(force=force_layers)
        except TypeError:
            update_layers()
    getattr(tab, "sort_layers", lambda: None)()
    tab.update_summary()
