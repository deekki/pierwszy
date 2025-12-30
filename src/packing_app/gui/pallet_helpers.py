"""Helper functions for pallet tab selection handling without GUI imports."""


def apply_pattern_selection_after_restore(tab, previous_flag: bool, target_key: str) -> bool:
    setattr(tab, "_suspend_pattern_apply", previous_flag)
    if not target_key:
        return False
    tree = getattr(tab, "pattern_tree", None)
    if tree is None:
        return False
    selection = tree.selection()
    if selection and selection[0] == target_key:
        tab.on_pattern_select()
        return True
    return False


def filter_selection_for_layer(selected_indices, layer_idx: int):
    return {(layer, idx) for layer, idx in selected_indices if layer == layer_idx}
