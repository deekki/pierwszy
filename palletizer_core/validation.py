from __future__ import annotations

from .engine import PalletInputs


ERROR_REQUIRED_DIMENSIONS = (
    "Wszystkie wymiary i liczba warstw muszą być większe od 0."
)


def validate_pallet_inputs(inputs: PalletInputs) -> list[str]:
    if (
        inputs.pallet_w == 0
        or inputs.pallet_l == 0
        or inputs.pallet_h == 0
        or inputs.box_w == 0
        or inputs.box_l == 0
        or inputs.box_h == 0
        or inputs.num_layers <= 0
    ):
        return [ERROR_REQUIRED_DIMENSIONS]
    return []
