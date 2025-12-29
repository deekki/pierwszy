from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Tuple, Dict, Set

from palletizer_core.signature import layout_signature

LayerRects = List[Tuple[float, float, float, float]]


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


def rects_to_pally_pattern(
    rects: Iterable[Tuple[float, float, float, float]],
    carton_w: float,
    carton_l: float,
    pallet_w: float,
    tol: float = 1.0,
) -> List[Dict]:
    del pallet_w
    pattern: List[Dict] = []
    for x, y, w, length in rects:
        x_center = x + w / 2.0
        y_center = y + length / 2.0
        if abs(w - carton_w) <= tol and abs(length - carton_l) <= tol:
            rot = 0
        elif abs(w - carton_l) <= tol and abs(length - carton_w) <= tol:
            rot = 90
        else:
            rot = 0
        pattern.append({"x": x_center, "y": y_center, "r": [rot], "g": [], "f": 1})
    return pattern


def mirror_pattern(pattern: Iterable[Dict], pallet_w: float) -> List[Dict]:
    rot_map = {0: 0, 90: 270, 180: 180, 270: 90}
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
    name: str,
    pallet_w: int,
    pallet_l: int,
    pallet_h: int,
    box_w: int,
    box_l: int,
    box_h: int,
    box_weight_g: int,
    layer_rects_list: List[LayerRects],
    slips_after: Set[int],
) -> Dict:
    num_layers = len(layer_rects_list)
    layer_types: List[Dict] = [
        {"name": "Shim paper: Default", "class": "separator", "height": 1}
    ]
    signature_to_name: Dict[tuple, str] = {}
    signature_to_pattern: Dict[tuple, List[Dict]] = {}
    layer_type_names: List[str] = []
    next_idx = 1

    for rects in layer_rects_list:
        signature = layout_signature(rects)
        if signature not in signature_to_name:
            layer_name = f"Layer type: {next_idx}"
            next_idx += 1
            pattern = rects_to_pally_pattern(rects, box_w, box_l, pallet_w)
            signature_to_name[signature] = layer_name
            signature_to_pattern[signature] = pattern
            layer_types.append(
                {
                    "name": layer_name,
                    "class": "layer",
                    "pattern": pattern,
                    "altPattern": mirror_pattern(pattern, pallet_w),
                    "approach": "inverse",
                    "altApproach": "inverse",
                }
            )
        layer_type_names.append(signature_to_name[signature])

    layers: List[str] = ["Shim paper: Default"]
    for idx, layer_name in enumerate(layer_type_names, start=1):
        layers.append(layer_name)
        if idx in slips_after:
            layers.append("Shim paper: Default")

    return {
        "name": name,
        "description": "",
        "dimensions": {
            "height": num_layers * box_h,
            "width": pallet_w,
            "length": pallet_l,
            "palletHeight": pallet_h,
        },
        "productDimensions": {
            "weight": box_weight_g,
            "height": box_h,
            "width": box_w,
            "length": box_l,
        },
        "maxGrip": 1,
        "maxGripAuto": False,
        "labelOrientation": 180,
        "guiSettings": {
            "PPB_VERSION_NO": "3.1.1",
            "boxPadding": 0,
            "units": "metric",
            "overhangSides": 0,
            "overhangEnds": 0,
            "altLayout": "mirror",
        },
        "dateModified": iso_utc_now_ms(),
        "layerTypes": layer_types,
        "layers": layers,
    }
