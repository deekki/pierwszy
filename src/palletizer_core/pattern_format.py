from __future__ import annotations

from typing import Any, Callable, Dict

from .units import parse_float


def _parse_dim(var: Any) -> float:
    try:
        val = parse_float(var.get())
        return max(0, val)
    except Exception:
        return 0.0


def gather_pattern_data(
    tab: Any, name: str = "", parse_dim: Callable[[Any], float] | None = None
) -> Dict[str, Any]:
    """Collect current pallet layout as a JSON-serialisable dict."""
    dim_parser = parse_dim or _parse_dim
    pallet_w = dim_parser(tab.pallet_w_var)
    pallet_l = dim_parser(tab.pallet_l_var)
    pallet_h = dim_parser(tab.pallet_h_var)
    box_w = dim_parser(tab.box_w_var)
    box_l = dim_parser(tab.box_l_var)
    box_h = dim_parser(tab.box_h_var)
    num_layers = getattr(tab, "num_layers", int(dim_parser(tab.num_layers_var)))
    data = {
        "name": name,
        "dimensions": {"width": pallet_w, "length": pallet_l, "height": pallet_h},
        "productDimensions": {"width": box_w, "length": box_l, "height": box_h},
        "layers": tab.layers[:num_layers],
    }
    return data


def apply_pattern_data(tab: Any, data: Dict[str, Any]) -> None:
    """Load pallet layout from a dictionary."""
    dims = data.get("dimensions", {})
    tab.pallet_w_var.set(str(dims.get("width", "")))
    tab.pallet_l_var.set(str(dims.get("length", "")))
    tab.pallet_h_var.set(str(dims.get("height", "")))
    prod = data.get("productDimensions", {})
    tab.box_w_var.set(str(prod.get("width", "")))
    tab.box_l_var.set(str(prod.get("length", "")))
    tab.box_h_var.set(str(prod.get("height", "")))
    layers = data.get("layers", [])
    if layers:
        tab.layers = [list(layer) for layer in layers]
        tab.carton_ids = [list(range(1, len(layer) + 1)) for layer in tab.layers]
        tab.num_layers = len(tab.layers)
        setter = getattr(tab, "_set_layer_field", None)
        if setter is not None and hasattr(tab, "num_layers_var"):
            setter(tab.num_layers_var, tab.num_layers)
        elif hasattr(tab, "num_layers_var") and hasattr(tab.num_layers_var, "set"):
            tab.num_layers_var.set(str(tab.num_layers))
        tab.layer_patterns = ["" for _ in tab.layers]
        tab.transformations = ["Brak" for _ in tab.layers]
        if hasattr(tab, "undo_stack"):
            tab.undo_stack.clear()
        tab.draw_pallet()
        tab.update_summary()
