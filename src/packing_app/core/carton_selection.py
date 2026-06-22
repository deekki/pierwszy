from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Iterable, Sequence

from palletizer_core.engine import PalletInputs, build_layouts


@dataclass(frozen=True)
class CartonRecommendation:
    carton_name: str
    pieces_per_carton: int
    carton_volume_eff: float
    orientation: tuple[float, float, float]
    cartons_per_layer: int
    layers: int
    cartons_per_pallet: int
    products_per_pallet: int
    pallet_height: float
    pallet_mass: float | None
    status: str


def best_product_fit(carton_dims: Sequence[float], product_dims: Sequence[float], clearance: float = 0.0):
    cw, cl, ch = [float(v) for v in carton_dims]
    best = (0, 0.0, (0.0, 0.0, 0.0))
    for pw, pl, ph in set(permutations([float(v) for v in product_dims], 3)):
        ew, el, eh = pw + clearance, pl + clearance, ph + clearance
        if min(ew, el, eh) <= 0:
            continue
        count = int(cw // ew) * int(cl // el) * int(ch // eh)
        eff = count * pw * pl * ph / (cw * cl * ch) if cw > 0 and cl > 0 and ch > 0 else 0.0
        if (count, eff) > (best[0], best[1]):
            best = (count, eff, (pw, pl, ph))
    return best


def rank_cartons(
    cartons: dict[str, Sequence[float]],
    pallets: Iterable[dict],
    *,
    product_dims: Sequence[float],
    product_mass: float | None = None,
    max_pallet_height: float = 1600.0,
    include_pallet_height: bool = True,
    clearance: float = 0.0,
    max_pallet_mass: float = 600.0,
    thickness: float = 3.0,
) -> list[CartonRecommendation]:
    pallet = next(iter(pallets), {"w": 1200, "l": 800, "h": 144, "weight": 0})
    results: list[CartonRecommendation] = []
    for name, dims in cartons.items():
        if len(dims) < 3:
            continue
        cw, cl, ch = [float(v) for v in dims[:3]]
        pieces, vol_eff, orientation = best_product_fit((cw, cl, ch), product_dims, clearance)
        if pieces <= 0:
            results.append(CartonRecommendation(name, 0, 0.0, orientation, 0, 0, 0, 0, 0.0, None, "nie mieści się"))
            continue
        usable = max_pallet_height - (float(pallet.get("h", 0)) if include_pallet_height else 0)
        layer_h = ch + 2 * thickness
        layers = max(int(usable // layer_h), 0) if usable > 0 and layer_h > 0 else 1
        inputs = PalletInputs(float(pallet.get("w", 1200)), float(pallet.get("l", 800)), float(pallet.get("h", 0)), cw, cl, ch, thickness, 0, 0, max(layers, 1), max_pallet_height, include_pallet_height)
        comp = build_layouts(inputs, False, False, "Cała warstwa", False, filter_sanity=False, result_limit=1)
        cartons_per_layer = len(comp.best_odd)
        cartons_per_pallet = cartons_per_layer * layers
        products = cartons_per_pallet * pieces
        height = layers * layer_h + (float(pallet.get("h", 0)) if include_pallet_height else 0)
        mass = products * product_mass + float(pallet.get("weight", 0)) if product_mass is not None and product_mass > 0 else None
        warnings = []
        if height > max_pallet_height > 0:
            warnings.append("za wysoka paleta")
        if mass is not None and mass > max_pallet_mass > 0:
            warnings.append("za ciężka paleta")
        if vol_eff < 0.35:
            warnings.append("słabe wykorzystanie")
        results.append(CartonRecommendation(name, pieces, vol_eff, orientation, cartons_per_layer, layers, cartons_per_pallet, products, height, mass, ", ".join(warnings) if warnings else "OK"))
    return sorted(results, key=lambda r: (-r.products_per_pallet, -r.carton_volume_eff, r.pallet_height))
