from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Set, Tuple

from palletizer_core.signature import layout_signature

LayerRects = List[Tuple[float, float, float, float]]

logger = logging.getLogger(__name__)


@dataclass
class PallyExportConfig:
    name: str
    pallet_w: int
    pallet_l: int
    pallet_h: int
    box_w: int
    box_l: int
    box_h: int
    box_weight_g: int
    overhang_ends: int
    overhang_sides: int
    box_padding: int = 0
    label_orientation: int = 180
    alt_layout: str = "mirror"
    units: str = "metric"
    swap_axes_for_pally: Optional[bool] = None
    quant_step_mm: float = 0.5
    signature_eps_mm: float = 0.5
    approach: str = "normal"
    alt_approach: str = "normal"
    placement_sequence: str = "default"
    pallet_height_override: Optional[int] = None
    dimensions_height_override: Optional[int] = None
    omit_altpattern_when_mirror: bool = False

    def __post_init__(self) -> None:
        if self.swap_axes_for_pally is None:
            self.swap_axes_for_pally = self.pallet_w > self.pallet_l


def iso_utc_now_ms() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def parse_slips_after(text: str, max_layers: int) -> Set[int]:
    slips: Set[int] = set()
    if not text:
        return slips
    for chunk in text.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            value = int(chunk)
        except ValueError:
            continue
        if value <= 0:
            continue
        if max_layers and value > max_layers:
            continue
        slips.add(value)
    return slips


def _swap_rect_axes(rects: Iterable[Tuple[float, float, float, float]]) -> List[Tuple[float, float, float, float]]:
    swapped: List[Tuple[float, float, float, float]] = []
    for x, y, w, length in rects:
        swapped.append((y, x, length, w))
    return swapped


def _quantize(value: float, step: float) -> float:
    quantized = Decimal(str(value)) / Decimal(str(step))
    snapped = quantized.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return float(snapped * Decimal(str(step)))


def _normalize_angle(value: int) -> int:
    return value % 360


def _label_direction(label_orientation: int, rotation: int) -> int:
    return _normalize_angle(label_orientation + rotation)


def _sort_pattern_items(
    items: List[Tuple[Dict, Tuple[float, float, float, float]]],
    placement_sequence: str,
    pallet_w: float,
    pallet_l: float,
    quant_step_mm: float,
) -> List[Tuple[Dict, Tuple[float, float, float, float]]]:
    if placement_sequence == "columns":
        return sorted(items, key=lambda item: (item[0].get("x", 0), item[0].get("y", 0)))

    if placement_sequence in {"rows", "default"}:
        return sorted(items, key=lambda item: (item[0].get("y", 0), item[0].get("x", 0)))

    if placement_sequence == "center":
        cx = pallet_w / 2.0
        cy = pallet_l / 2.0
        return sorted(
            items,
            key=lambda item: (
                abs(item[0].get("x", 0) - cx) + abs(item[0].get("y", 0) - cy),
                item[0].get("y", 0),
                item[0].get("x", 0),
            ),
        )

    if placement_sequence == "snake":
        tol = max(quant_step_mm, 1e-6)
        rows: Dict[float, List[Tuple[Dict, Tuple[float, float, float, float]]]] = {}
        for item in items:
            y = item[0].get("y", 0)
            key = round(y / tol) * tol
            rows.setdefault(key, []).append(item)
        ordered: List[Tuple[Dict, Tuple[float, float, float, float]]] = []
        for idx, key in enumerate(sorted(rows.keys())):
            row_items = sorted(rows[key], key=lambda itm: itm[0].get("x", 0))
            if idx % 2:
                row_items.reverse()
            ordered.extend(row_items)
        return ordered

    return sorted(items, key=lambda item: (item[0].get("y", 0), item[0].get("x", 0)))


def rects_to_pally_pattern(
    rects: Iterable[Tuple[float, float, float, float]],
    carton_w: float,
    carton_l: float,
    pallet_w: float,
    pallet_l: float,
    quant_step_mm: float,
    label_orientation: Optional[int],
    placement_sequence: str = "default",
) -> Tuple[List[Dict], List[Tuple[float, float, float, float]]]:
    pattern_with_signatures: List[Tuple[Dict, Tuple[float, float, float, float]]] = []

    def _rotation_for_rect(
        x_center: float, y_center: float, w: float, length: float
    ) -> int:
        orientation_error_0 = abs(w - carton_w) + abs(length - carton_l)
        orientation_error_90 = abs(w - carton_l) + abs(length - carton_w)
        base_rot = 0 if orientation_error_0 <= orientation_error_90 else 90
        flipped_rot = (base_rot + 180) % 360

        if label_orientation is None:
            return base_rot

        is_y_aligned = base_rot in (0, 180)
        pallet_half_x = pallet_w / 2.0
        pallet_half_y = pallet_l / 2.0

        if is_y_aligned:
            desired_dir = 0 if y_center <= pallet_half_y else 180
        else:
            desired_dir = 270 if x_center <= pallet_half_x else 90

        base_dir = _label_direction(label_orientation, base_rot)
        flipped_dir = _label_direction(label_orientation, flipped_rot)

        if base_dir == flipped_dir:
            return base_rot
        if desired_dir == base_dir:
            return base_rot
        if desired_dir == flipped_dir:
            return flipped_rot
        return base_rot

    for x, y, w, length in rects:
        x_center = _quantize(x + w / 2.0, quant_step_mm)
        y_center = _quantize(y + length / 2.0, quant_step_mm)

        rot = _rotation_for_rect(x_center, y_center, w, length)
        w_eff, l_eff = (carton_w, carton_l) if rot in (0, 180) else (carton_l, carton_w)
        w_eff = _quantize(w_eff, quant_step_mm)
        l_eff = _quantize(l_eff, quant_step_mm)

        pattern_with_signatures.append(
            (
                {"x": x_center, "y": y_center, "r": [rot], "g": [], "f": 1},
                (
                    x_center - w_eff / 2.0,
                    y_center - l_eff / 2.0,
                    w_eff,
                    l_eff,
                ),
            )
        )

    ordered = _sort_pattern_items(
        pattern_with_signatures,
        placement_sequence=placement_sequence,
        pallet_w=pallet_w,
        pallet_l=pallet_l,
        quant_step_mm=quant_step_mm,
    )
    sorted_pattern, sorted_signature_rects = zip(*ordered) if ordered else ([], [])
    return list(sorted_pattern), list(sorted_signature_rects)


def mirror_pattern(pattern: Iterable[Dict], pallet_w: float) -> List[Dict]:
    rot_map = {angle: (360 - angle) % 360 for angle in (0, 90, 180, 270)}
    mirrored: List[Dict] = []
    for item in pattern:
        rot_value = item.get("r", [0])[0]
        mirrored.append(
            {
                "x": pallet_w - item["x"],
                "y": item["y"],
                "r": [rot_map.get(rot_value, rot_value)],
                "g": list(item.get("g", [])),
                "f": item.get("f", 1),
            }
        )
    return mirrored


def build_pally_json(
    config: PallyExportConfig,
    layer_rects_list: List[LayerRects],
    slips_after: Set[int],
    include_base_slip: bool = True,
    manual_orders_by_signature: Optional[Dict[str, List[int]]] = None,
    manual_orders_alt_by_signature: Optional[Dict[str, List[int]]] = None,
    manual_orders_by_signature_right: Optional[Dict[str, List[int]]] = None,
    manual_orders_by_signature_left: Optional[Dict[str, List[int]]] = None,
) -> Dict:
    num_layers = len(layer_rects_list)
    swap_axes = bool(config.swap_axes_for_pally)
    pallet_width = min(config.pallet_w, config.pallet_l) if swap_axes else config.pallet_w
    pallet_length = max(config.pallet_w, config.pallet_l) if swap_axes else config.pallet_l
    carton_w = config.box_l if swap_axes else config.box_w
    carton_l = config.box_w if swap_axes else config.box_l

    layer_types: List[Dict] = [
        {"name": "Shim paper: Default", "class": "separator", "height": 1}
    ]
    signature_to_name: Dict[tuple, str] = {}
    layer_type_names: List[str] = []
    next_idx = 1

    manual_orders_right = (
        manual_orders_by_signature_right
        or manual_orders_by_signature
        or {}
    )
    manual_orders_left = (
        manual_orders_by_signature_left
        if manual_orders_by_signature_left is not None
        else manual_orders_alt_by_signature
    )
    if manual_orders_left is None:
        manual_orders_left = manual_orders_right

    def _apply_sequence(
        pattern: List[Dict],
        manual_order: Optional[List[int]],
        approach: str,
        label: str,
    ) -> List[Dict]:
        if manual_order:
            if len(manual_order) != len(pattern):
                logger.warning(
                    "Manual permutation length mismatch for %s: %s != %s",  # noqa: TRY400
                    label,
                    len(manual_order),
                    len(pattern),
                )
            else:
                return [pattern[idx] for idx in manual_order]
        if approach == "inverse":
            return list(reversed(pattern))
        return pattern

    for rects in layer_rects_list:
        rects_to_use = _swap_rect_axes(rects) if swap_axes else rects
        pattern, signature_rects = rects_to_pally_pattern(
            rects_to_use,
            carton_w,
            carton_l,
            pallet_width,
            pallet_length,
            quant_step_mm=config.quant_step_mm,
            label_orientation=config.label_orientation,
            placement_sequence=config.placement_sequence,
        )
        signature = layout_signature(signature_rects, eps=config.signature_eps_mm)
        manual_order = manual_orders_right.get(str(signature))
        manual_order_alt = manual_orders_left.get(str(signature))
        if signature not in signature_to_name:
            layer_name = f"Layer type: {next_idx}"
            next_idx += 1
            signature_to_name[signature] = layer_name
            omit_altpattern = (
                config.alt_layout == "mirror" and config.omit_altpattern_when_mirror
            )
            pattern = _apply_sequence(
                pattern, manual_order, config.approach, f"signature {signature}"
            )
            if omit_altpattern:
                layer_type = {
                    "name": layer_name,
                    "class": "layer",
                    "pattern": pattern,
                    "approach": config.approach,
                    "altApproach": config.alt_approach,
                }
            else:
                alt_pattern = (
                    list(pattern)
                    if config.alt_layout == "altPattern"
                    else mirror_pattern(pattern, pallet_width)
                )
                alt_pattern = _apply_sequence(
                    alt_pattern,
                    manual_order_alt,
                    config.alt_approach,
                    f"alt signature {signature}",
                )
                layer_type = {
                    "name": layer_name,
                    "class": "layer",
                    "pattern": pattern,
                    "altPattern": alt_pattern,
                    "approach": config.approach,
                    "altApproach": config.alt_approach,
                }
            layer_types.append(layer_type)
        layer_type_names.append(signature_to_name[signature])

    layers: List[str] = []
    if include_base_slip:
        layers.append("Shim paper: Default")
    for idx, layer_name in enumerate(layer_type_names, start=1):
        layers.append(layer_name)
        if idx in slips_after:
            layers.append("Shim paper: Default")

    pallet_height = (
        config.pallet_height_override
        if config.pallet_height_override is not None
        else config.pallet_h
    )
    dimensions_height = (
        config.dimensions_height_override
        if config.dimensions_height_override is not None
        else num_layers * config.box_h
    )

    return {
        "name": config.name,
        "description": "",
        "dimensions": {
            "height": dimensions_height,
            "width": pallet_width,
            "length": pallet_length,
            "palletHeight": pallet_height,
        },
        "productDimensions": {
            "weight": config.box_weight_g,
            "height": config.box_h,
            "width": carton_w,
            "length": carton_l,
        },
        "maxGrip": 1,
        "maxGripAuto": False,
        "labelOrientation": config.label_orientation,
        "guiSettings": {
            "PPB_VERSION_NO": "3.1.1",
            "boxPadding": config.box_padding,
            "units": config.units,
            "overhangSides": config.overhang_sides,
            "overhangEnds": config.overhang_ends,
            "altLayout": config.alt_layout,
        },
        "dateModified": iso_utc_now_ms(),
        "layerTypes": layer_types,
        "layers": layers,
    }


def find_out_of_bounds(payload: Dict) -> List[str]:
    pallet_width = float(payload.get("dimensions", {}).get("width", 0))
    pallet_length = float(payload.get("dimensions", {}).get("length", 0))
    product_width = float(payload.get("productDimensions", {}).get("width", 0))
    product_length = float(payload.get("productDimensions", {}).get("length", 0))
    gui_settings = payload.get("guiSettings", {})
    overhang_sides = float(gui_settings.get("overhangSides", 0))
    overhang_ends = float(gui_settings.get("overhangEnds", 0))

    layer_types_lookup = {lt.get("name"): lt for lt in payload.get("layerTypes", [])}
    messages: List[str] = []
    layer_counter = 0
    for layer_name in payload.get("layers", []):
        layer_type = layer_types_lookup.get(layer_name)
        if not layer_type or layer_type.get("class") == "separator":
            continue
        layer_counter += 1
        for item in layer_type.get("pattern", []):
            rot = item.get("r", [0])[0]
            w_eff, l_eff = (
                (product_width, product_length)
                if rot in (0, 180)
                else (product_length, product_width)
            )
            x_center = float(item.get("x", 0))
            y_center = float(item.get("y", 0))
            left = x_center - w_eff / 2.0
            right = x_center + w_eff / 2.0
            bottom = y_center - l_eff / 2.0
            top = y_center + l_eff / 2.0

            if left < -overhang_sides:
                diff = -overhang_sides - left
                messages.append(
                    f"Warstwa {layer_counter}: lewa krawędź poza zakresem o {diff:.1f} mm"
                )
            if right > pallet_width + overhang_sides:
                diff = right - (pallet_width + overhang_sides)
                messages.append(
                    f"Warstwa {layer_counter}: prawa krawędź poza zakresem o {diff:.1f} mm"
                )
            if bottom < 0:
                diff = -bottom
                messages.append(
                    f"Warstwa {layer_counter}: dolna krawędź poza zakresem o {diff:.1f} mm"
                )
            if top > pallet_length + overhang_ends:
                diff = top - (pallet_length + overhang_ends)
                messages.append(
                    f"Warstwa {layer_counter}: górna krawędź poza zakresem o {diff:.1f} mm"
                )
    return messages
