from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from packing_app.core.pallet_snapshot import PalletSnapshot

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from palletizer_core.engine import PalletInputs
    from packing_app.gui.tab_pallet import TabPallet


def _prepare_transformations(tab: "TabPallet", layer_count: int) -> list[str]:
    transformations = list(tab.transformations[:layer_count])
    if len(transformations) < layer_count:
        transformations.extend([""] * (layer_count - len(transformations)))
    return transformations


def build_snapshot_from_tab(
    tab: "TabPallet", *, inputs: "PalletInputs" | None = None, include_box_weight: bool = False
) -> PalletSnapshot | None:
    try:
        inputs = inputs or tab._read_inputs()
    except Exception:
        logger.exception("Failed to read pallet inputs for snapshot")
        return None

    layer_count = len(tab.layers)
    if not layer_count:
        return None

    inputs.num_layers = layer_count
    transformations = _prepare_transformations(tab, layer_count)

    kwargs = {"transform_func": tab.apply_transformation, "slips_after": set()}
    if include_box_weight:
        box_weight_kg, weight_source = tab._get_active_carton_weight()
        kwargs.update(
            {
                "box_weight_g": int(round(max(box_weight_kg, 0.0) * 1000)),
                "box_weight_source": (weight_source or "unknown"),
            }
        )

    try:
        snapshot = PalletSnapshot.from_layers(
            inputs=inputs,
            layers=tab.layers,
            transformations=transformations,
            **kwargs,
        )
    except Exception:
        logger.exception("Failed to build pallet snapshot")
        return None

    return snapshot
