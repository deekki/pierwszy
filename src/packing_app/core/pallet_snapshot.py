from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List, Sequence, Set

from palletizer_core.engine import LayerLayout, PalletInputs
from palletizer_core.transformations import apply_transformation


TransformFunc = Callable[[LayerLayout, str, float, float], LayerLayout]


@dataclass
class PalletSnapshot:
    pallet_w: float
    pallet_l: float
    pallet_h: float
    box_w: float
    box_l: float
    box_h: float
    thickness: float
    spacing: float
    slip_count: int
    num_layers: int
    layers: List[LayerLayout]
    transformations: List[str]
    layer_rects_list: List[LayerLayout]
    slips_after: Set[int]
    box_weight_g: int | None = None
    box_weight_source: str = "unknown"

    @classmethod
    def from_layers(
        cls,
        inputs: PalletInputs,
        layers: Sequence[LayerLayout],
        transformations: Sequence[str] | None,
        slips_after: Iterable[int],
        *,
        box_weight_g: int | None = None,
        box_weight_source: str = "unknown",
        transform_func: TransformFunc | None = None,
    ) -> "PalletSnapshot":
        transform_func = transform_func or apply_transformation
        normalized_transformations = list(transformations or [])
        if normalized_transformations and len(normalized_transformations) != len(layers):
            raise ValueError("Transformations length must match layers length")
        if not normalized_transformations:
            normalized_transformations = ["Brak" for _ in layers]

        layer_rects_list: List[LayerLayout] = []
        for layout, transform in zip(layers, normalized_transformations):
            coords = transform_func(list(layout), transform, inputs.pallet_w, inputs.pallet_l)
            layer_rects_list.append(coords)

        return cls(
            pallet_w=inputs.pallet_w,
            pallet_l=inputs.pallet_l,
            pallet_h=inputs.pallet_h,
            box_w=inputs.box_w,
            box_l=inputs.box_l,
            box_h=inputs.box_h,
            thickness=inputs.thickness,
            spacing=inputs.spacing,
            slip_count=inputs.slip_count,
            num_layers=inputs.num_layers,
            box_weight_g=box_weight_g if box_weight_g is None else int(box_weight_g),
            box_weight_source=box_weight_source,
            layers=[list(layer) for layer in layers],
            transformations=list(normalized_transformations),
            layer_rects_list=layer_rects_list,
            slips_after=set(slips_after),
        )

