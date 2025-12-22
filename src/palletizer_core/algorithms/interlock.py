from .rect_packing import pack_rectangles_mixed_greedy


def compute_interlocked_layout(
    pallet_w, pallet_l, box_w, box_l, num_layers=4, shift_even=True
):
    """Return positions for standard and interlocked stacking.

    Parameters
    ----------
    pallet_w, pallet_l : float
        Dimensions of the pallet in mm.
    box_w, box_l : float
        Dimensions of the carton in mm.
    num_layers : int, optional
        Number of layers to generate. Default is 4.
    shift_even : bool, optional
        If ``True`` (default), even layers (2nd, 4th, ...) are shifted.
        If ``False``, odd layers are shifted instead.
    """
    count, base_positions = pack_rectangles_mixed_greedy(
        pallet_w, pallet_l, box_w, box_l
    )
    if not base_positions:
        empty_layers = [[] for _ in range(num_layers)]
        return 0, empty_layers, empty_layers

    base_layers = [list(base_positions) for _ in range(num_layers)]

    min_x = min(x for x, y, w, h in base_positions)
    max_x = max(x + w for x, y, w, h in base_positions)
    min_y = min(y for x, y, w, h in base_positions)
    max_y = max(y + h for x, y, w, h in base_positions)

    shift_x = 0.0
    shift_y = 0.0
    if min_x >= box_w / 2 and max_x + box_w / 2 <= pallet_w:
        shift_x = box_w / 2
    elif min_y >= box_l / 2 and max_y + box_l / 2 <= pallet_l:
        shift_y = box_l / 2

    interlocked_layers = []
    for layer_idx in range(num_layers):
        is_even = layer_idx % 2 == 1  # 1-based: even layer when index is odd
        should_shift = (shift_even and is_even) or (not shift_even and not is_even)
        if should_shift:
            shifted = [
                (x + shift_x, y + shift_y, w, h) for x, y, w, h in base_positions
            ]
            interlocked_layers.append(shifted)
        else:
            interlocked_layers.append(base_positions)

    return count, base_layers, interlocked_layers
