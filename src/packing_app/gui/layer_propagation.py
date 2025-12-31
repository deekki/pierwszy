from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

Box = Tuple[float, float, float, float]


def _matching_carton_index(
    reference_box: Box,
    target_layer: Sequence[Box],
    *,
    size_tol: float,
    position_tol: float,
) -> Optional[int]:
    """Return the index of a carton matching ``reference_box`` in ``target_layer``.

    A match requires a box with the same dimensions (within ``size_tol``) and a
    position within ``position_tol`` of the reference.
    """

    ref_x, ref_y, ref_w, ref_h = reference_box
    best: tuple[float, int] | None = None
    for idx, (x, y, w, h) in enumerate(target_layer):
        if not math.isclose(w, ref_w, abs_tol=size_tol):
            continue
        if not math.isclose(h, ref_h, abs_tol=size_tol):
            continue
        distance = math.hypot(x - ref_x, y - ref_y)
        if distance <= position_tol and (best is None or distance < best[0]):
            best = (distance, idx)

    return None if best is None else best[1]


def propagate_carton_delta(
    layers: List[List[Box]],
    layer_patterns: Sequence[str],
    source_layer_idx: int,
    carton_idx: int,
    delta: Tuple[float, float],
    *,
    size_tol: float = 1e-6,
    position_tol: float = 1e-3,
    include_source: bool = False,
    allowed_layers: Sequence[int] | None = None,
    reference_box: Box | None = None,
) -> list[tuple[int, int]]:
    """Apply ``delta`` to matching cartons across layers with the same pattern.

    The source carton is identified by ``source_layer_idx`` and ``carton_idx``.
    A carton in another layer matches when it has the same pattern id, the same
    dimensions (within ``size_tol``) and is positioned within ``position_tol``
    of the source carton.

    If ``allowed_layers`` is provided, updates are limited to those indices.
    If ``reference_box`` is provided it is used for matching instead of the
    current position in ``layers``. Returns a list of ``(layer_idx, carton_idx)``
    pairs that were updated.
    """

    if source_layer_idx >= len(layers) or carton_idx >= len(layers[source_layer_idx]):
        return []

    pattern = layer_patterns[source_layer_idx] if source_layer_idx < len(layer_patterns) else None
    if pattern is None:
        return []

    reference = reference_box or layers[source_layer_idx][carton_idx]
    updated: list[tuple[int, int]] = []
    for layer_idx, layer_pattern in enumerate(layer_patterns):
        if layer_pattern != pattern or layer_idx >= len(layers):
            continue
        if layer_idx == source_layer_idx and not include_source:
            continue
        if allowed_layers is not None and layer_idx not in allowed_layers:
            continue

        if layer_idx == source_layer_idx:
            match_idx = carton_idx
        else:
            match_idx = _matching_carton_index(
                reference,
                layers[layer_idx],
                size_tol=size_tol,
                position_tol=position_tol,
            )

        if match_idx is None:
            continue

        x, y, w, h = layers[layer_idx][match_idx]
        layers[layer_idx][match_idx] = (x + delta[0], y + delta[1], w, h)
        updated.append((layer_idx, match_idx))

    return updated
