from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Tuple

import yaml
import os

from packing_app.core import algorithms

from .models import Carton, Pallet

# Pattern is list of rectangles (x, y, w, l)
Pattern = List[Tuple[float, float, float, float]]


DEFAULT_WEIGHTS = {
    "layer_eff": 1.0,
    "cube_eff": 1.0,
    "stability": 1.0,
    "grip_changes": 1.0,
}


@lru_cache(maxsize=None)
def load_weights() -> Dict[str, float]:
    """Load scoring weights from settings.yaml if present."""
    settings_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "settings.yaml"
    )
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}
    else:
        data = {}

    weights = DEFAULT_WEIGHTS.copy()
    for key in DEFAULT_WEIGHTS:
        if key in data:
            try:
                weights[key] = float(data[key])
            except (TypeError, ValueError):
                pass
    return weights


@dataclass
class PatternScore:
    """Simple container for pattern metrics."""

    name: str
    layer_eff: float
    cube_eff: float
    stability: float
    grip_changes: int
    penalty: float = field(init=False)

    def __post_init__(self) -> None:
        weights = load_weights()
        self.penalty = (
            -(
                weights["layer_eff"] * self.layer_eff
                + weights["cube_eff"] * self.cube_eff
                + weights["stability"] * self.stability
            )
            + weights["grip_changes"] * self.grip_changes
        )


class PatternSelector:
    """Generate → score → rank pallet patterns."""

    def __init__(
        self,
        carton: Carton,
        pallet: Pallet,
        *,
        padding_mm: int = 0,
        overhang_mm: Tuple[int, int] = (0, 0),
    ) -> None:
        self.carton = carton
        self.pallet = pallet
        self.padding = padding_mm
        self.overhang = overhang_mm

    def _eff_dims(self) -> Tuple[float, float, float, float]:
        pallet_w = self.pallet.width + self.overhang[0] * 2
        pallet_l = self.pallet.length + self.overhang[1] * 2
        box_w = self.carton.width + self.padding * 2
        box_l = self.carton.length + self.padding * 2
        return pallet_w, pallet_l, box_w, box_l

    def generate_all(self, *, maximize_mixed: bool = False) -> Dict[str, Pattern]:
        """Return raw patterns keyed by algorithm name.

        Parameters
        ----------
        maximize_mixed : bool, optional
            If ``True``, apply :func:`maximize_mixed_layout` after the greedy
            mixed layout to obtain a denser variant.
        """
        pallet_w, pallet_l, box_w, box_l = self._eff_dims()
        patterns: Dict[str, Pattern] = {}

        # column layout
        _, patt = algorithms.pack_rectangles_2d(pallet_w, pallet_l, box_w, box_l)
        patterns["column"] = patt

        # row-by-row layout
        _, row_patt = algorithms.pack_rectangles_row_by_row(
            pallet_w, pallet_l, box_w, box_l
        )
        patterns["row_by_row"] = row_patt

        # pinwheel layout
        _, pinwheel_patt = algorithms.pack_pinwheel(
            pallet_w, pallet_l, box_w, box_l
        )
        patterns["pinwheel"] = pinwheel_patt

        # L pattern layout
        _, l_patt = algorithms.pack_l_pattern(
            pallet_w, pallet_l, box_w, box_l
        )
        patterns["l_pattern"] = l_patt

        # interlock layout - use first layer of result
        try:
            _, _, inter = algorithms.compute_interlocked_layout(
                pallet_w, pallet_l, box_w, box_l, num_layers=1
            )
            patterns["interlock"] = inter[0] if inter else []
        except Exception:
            # Gracefully handle invalid dimensions and still expose an entry
            patterns["interlock"] = []

        # mixed greedy
        _, mixed = algorithms.pack_rectangles_mixed_greedy(
            pallet_w, pallet_l, box_w, box_l
        )
        patterns["mixed"] = mixed

        # optionally maximize the mixed layout for higher density
        if maximize_mixed:
            _, dense = algorithms.maximize_mixed_layout(
                pallet_w, pallet_l, box_w, box_l, 0, mixed
            )
            patterns["mixed_max"] = dense

        # dynamic layout using a full search
        _, dynamic = algorithms.pack_rectangles_dynamic(
            pallet_w, pallet_l, box_w, box_l
        )
        patterns["dynamic"] = dynamic

        return patterns

    def score(self, pattern: Pattern) -> PatternScore:
        """Weighted score; weights configurable in settings.yaml."""
        pallet_area = self.pallet.width * self.pallet.length
        box_area = self.carton.width * self.carton.length
        layer_eff = len(pattern) * box_area / pallet_area
        cube_eff = layer_eff  # simplified: same as area efficiency

        # Stability metric based on center of mass and support area
        # -----------------------------------------------------------------
        # The layout's center of mass (COM) is compared with the pallet
        # center; large offsets reduce stability.  Layouts that extend
        # beyond the pallet bounds (overhang) lose stability in proportion
        # to the fraction of their area that is unsupported.
        if pattern:
            com_x = sum(x + w / 2 for x, _, w, _ in pattern) / len(pattern)
            com_y = sum(y + length / 2 for _, y, _, length in pattern) / len(pattern)
            center_x = self.pallet.width / 2
            center_y = self.pallet.length / 2
            dist = ((com_x - center_x) ** 2 + (com_y - center_y) ** 2) ** 0.5
            max_dist = min(self.pallet.width, self.pallet.length) / 2
            com_factor = max(0.0, 1 - dist / max_dist)

            total_inside = 0.0
            for x, y, w, length in pattern:
                overlap_w = max(0.0, min(x + w, self.pallet.width) - max(x, 0.0))
                overlap_l = max(0.0, min(y + length, self.pallet.length) - max(y, 0.0))
                total_inside += overlap_w * overlap_l
            support_fraction = total_inside / (len(pattern) * box_area)

            stability = com_factor * support_fraction
        else:
            stability = 0.0
        grip_changes = 0
        return PatternScore("", layer_eff, cube_eff, stability, grip_changes)

    def best(
        self, *, maximize_mixed: bool = False
    ) -> Tuple[str, Pattern, PatternScore]:
        """Highest total score (lower penalty = better)."""
        patterns = self.generate_all(maximize_mixed=maximize_mixed)
        best_name = ""
        best_pattern: Pattern = []
        best_score: PatternScore | None = None
        for name, patt in patterns.items():
            score = self.score(patt)
            score.name = name
            if best_score is None or score.penalty < best_score.penalty:
                best_name = name
                best_pattern = patt
                best_score = score
        assert best_score is not None
        return best_name, best_pattern, best_score
