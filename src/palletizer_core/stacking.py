from __future__ import annotations


def compute_num_layers(
    max_stack: float,
    box_h: float,
    thickness: float,
    slip_count: int,
    include_pallet_height: bool,
    pallet_h: float,
) -> int:
    layer_height = box_h + 2 * thickness
    include_height = pallet_h if include_pallet_height else 0
    if layer_height <= 0 or max_stack <= 0:
        return 0
    available = max(max_stack - include_height, 0)
    return max(int(available // layer_height), 0)


def compute_max_stack(
    num_layers: int,
    box_h: float,
    thickness: float,
    slip_count: int,
    include_pallet_height: bool,
    pallet_h: float,
) -> float:
    layer_height = box_h + 2 * thickness
    include_height = pallet_h if include_pallet_height else 0
    if layer_height <= 0 or num_layers <= 0:
        return 0
    return num_layers * layer_height + include_height
