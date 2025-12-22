from __future__ import annotations

from typing import List, Tuple


LayerLayout = List[Tuple[float, float, float, float]]


def apply_transformation(
    positions: LayerLayout, transform: str, pallet_w: float, pallet_l: float
) -> LayerLayout:
    new_positions: LayerLayout = []
    for x, y, w, h in positions:
        if transform == "Brak":
            new_positions.append((x, y, w, h))
        elif transform == "Odbicie wzdłuż dłuższego boku":
            if pallet_w >= pallet_l:
                new_x = pallet_w - x - w
                new_y = y
            else:
                new_x = x
                new_y = pallet_l - y - h
            new_positions.append((new_x, new_y, w, h))
        elif transform == "Odbicie wzdłuż krótszego boku":
            if pallet_w < pallet_l:
                new_x = pallet_w - x - w
                new_y = y
            else:
                new_x = x
                new_y = pallet_l - y - h
            new_positions.append((new_x, new_y, w, h))
        elif transform == "Obrót 180°":
            new_x = pallet_w - x - w
            new_y = pallet_l - y - h
            new_positions.append((new_x, new_y, w, h))
    return new_positions


def inverse_transformation(
    positions: LayerLayout, transform: str, pallet_w: float, pallet_l: float
) -> LayerLayout:
    """Reverse the transformation applied to the positions."""
    new_positions: LayerLayout = []
    for x, y, w, h in positions:
        new_positions.extend(
            apply_transformation(
                [(x, y, w, h)],
                transform,
                pallet_w,
                pallet_l,
            )
        )
    return new_positions
