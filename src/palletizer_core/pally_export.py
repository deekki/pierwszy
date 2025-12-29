from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Set, Tuple

from palletizer_core.signature import layout_signature

LayerRects = List[Tuple[float, float, float, float]]


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
    approach: str = "inverse"
    alt_approach: str = "inverse"

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


def _nearest_edge(pallet_w: float, pallet_l: float, x: float, y: float) -> str:
    distances = [
        (x, "left"),
        (pallet_w - x, "right"),
        (y, "front"),
        (pallet_l - y, "back"),
    ]
    return min(distances, key=lambda item: (item[0], item[1]))[1]


def _expected_orientation_for_edge(edge: str) -> int:
    mapping = {"front": 0, "left": 270, "right": 90, "back": 180}
    return mapping[edge]


def rects_to_pally_pattern(
    rects: Iterable[Tuple[float, float, float, float]],
    carton_w: float,
    carton_l: float,
    pallet_w: float,
    pallet_l: float,
    quant_step_mm: float,
    label_orientation: int,
) -> Tuple[List[Dict], List[Tuple[float, float, float, float]]]:
    pattern: List[Dict] = []
    signature_rects: List[Tuple[float, float, float, float]] = []

    for x, y, w, length in rects:
        x_center = _quantize(x + w / 2.0, quant_step_mm)
        y_center = _quantize(y + length / 2.0, quant_step_mm)

        orientation_error_0 = abs(w - carton_w) + abs(length - carton_l)
        orientation_error_90 = abs(w - carton_l) + abs(length - carton_w)
        base_rot = 0 if orientation_error_0 <= orientation_error_90 else 90
        flipped_rot = (base_rot + 180) % 360

        nearest_edge = _nearest_edge(pallet_w, pallet_l, x_center, y_center)
        expected_orientation = _expected_orientation_for_edge(nearest_edge)
        base_dir = _label_direction(label_orientation, base_rot)
        flipped_dir = _label_direction(label_orientation, flipped_rot)

        if (base_dir == expected_orientation) != (flipped_dir == expected_orientation):
            rot = base_rot if base_dir == expected_orientation else flipped_rot
        elif base_dir == flipped_dir:
            rot = base_rot
        else:
            rot = base_rot

        w_eff, l_eff = (carton_w, carton_l) if rot in (0, 180) else (carton_l, carton_w)
        w_eff = _quantize(w_eff, quant_step_mm)
        l_eff = _quantize(l_eff, quant_step_mm)

        pattern.append({"x": x_center, "y": y_center, "r": [rot], "g": [], "f": 1})
        signature_rects.append(
            (
                x_center - w_eff / 2.0,
                y_center - l_eff / 2.0,
                w_eff,
                l_eff,
            )
        )

    def sort_key(item_rect):
        return (item_rect[0]["y"], item_rect[0]["x"])
    paired = list(zip(pattern, signature_rects))
    paired.sort(key=sort_key)
    sorted_pattern, sorted_signature_rects = zip(*paired) if paired else ([], [])
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
        )
        signature = layout_signature(signature_rects, eps=config.signature_eps_mm)
        if signature not in signature_to_name:
            layer_name = f"Layer type: {next_idx}"
            next_idx += 1
            signature_to_name[signature] = layer_name
            layer_types.append(
                {
                    "name": layer_name,
                    "class": "layer",
                    "pattern": pattern,
                    "altPattern": mirror_pattern(pattern, pallet_width),
                    "approach": config.approach,
                    "altApproach": config.alt_approach,
                }
            )
        layer_type_names.append(signature_to_name[signature])

    layers: List[str] = ["Shim paper: Default"]
    for idx, layer_name in enumerate(layer_type_names, start=1):
        layers.append(layer_name)
        if idx in slips_after:
            layers.append("Shim paper: Default")

    return {
        "name": config.name,
        "description": "",
        "dimensions": {
            "height": num_layers * config.box_h,
            "width": pallet_width,
            "length": pallet_length,
            "palletHeight": config.pallet_h,
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
