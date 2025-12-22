from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Tuple

import math

import os

try:  # pragma: no cover - exercised via tests when yaml is available
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - handled in load_weights
    yaml = None  # type: ignore

from packing_app.core import algorithms

from .metrics import (
    compute_edge_buffer_metrics,
    compute_edge_buffer_score,
    compute_edge_contact_fraction,
    compute_orientation_mix,
)
from .models import Carton, Pallet

# Pattern is list of rectangles (x, y, w, l)
Pattern = List[Tuple[float, float, float, float]]


DEFAULT_WEIGHTS = {
    "layer_eff": 1.0,
    "cube_eff": 1.0,
    "stability": 1.0,
    "grip_changes": 1.0,
}

RISK_STABILITY_THRESHOLD = 0.45
RISK_SUPPORT_THRESHOLD = 0.5
RISK_CONTACT_THRESHOLD = 0.25


def _fallback_parse_settings(stream) -> Dict[str, float]:
    """Parse simple ``key: value`` pairs without requiring PyYAML."""

    parsed: Dict[str, float] = {}
    for raw_line in stream:
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key or not value:
            continue
        try:
            parsed[key] = float(value)
        except ValueError:
            continue
    return parsed


@lru_cache(maxsize=None)
def load_weights() -> Dict[str, float]:
    """Load scoring weights from ``settings.yaml`` when available."""

    settings_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "settings.yaml"
    )
    data: Dict[str, float] = {}
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                if yaml is not None:
                    loaded = yaml.safe_load(f) or {}
                    if isinstance(loaded, dict):
                        data = {
                            key: float(value)
                            for key, value in loaded.items()
                            if isinstance(value, (int, float, str))
                        }
                else:
                    data = _fallback_parse_settings(f)
        except Exception:
            data = {}

    weights = DEFAULT_WEIGHTS.copy()
    for key in DEFAULT_WEIGHTS:
        if key in data:
            try:
                weights[key] = float(data[key])
            except (TypeError, ValueError):
                continue
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
    carton_count: int = 0
    support_fraction: float = 0.0
    min_support: float = 0.0
    edge_contact: float = 0.0
    edge_buffer: float = 0.0
    min_edge_clearance: float = 0.0
    orientation_mix: float = 0.0
    com_offset: float = 0.0
    instability_risk: bool = False
    warnings: List[str] = field(default_factory=list)
    weakest_carton: Tuple[float, float, float, float] | None = None
    weakest_support: float = 0.0
    display_name: str = ""

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

    def _edge_contact_fraction(self, pattern: Pattern) -> float:
        return compute_edge_contact_fraction(pattern)

    def _edge_buffer_metrics(self, pattern: Pattern) -> Tuple[float, float]:
        norm = max(1e-6, min(self.carton.width, self.carton.length) / 2.0)
        return compute_edge_buffer_metrics(
            pattern, self.pallet.width, self.pallet.length, norm
        )

    def _edge_buffer_score(self, pattern: Pattern) -> float:
        norm = max(1e-6, min(self.carton.width, self.carton.length) / 2.0)
        return compute_edge_buffer_score(
            pattern, self.pallet.width, self.pallet.length, norm
        )

    def _orientation_mix(self, pattern: Pattern) -> float:
        return compute_orientation_mix(
            pattern, default_orientation=self.carton.width >= self.carton.length
        )

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

        # rotated column layout
        if abs(box_w - box_l) > 1e-6:
            _, rotated = algorithms.pack_rectangles_2d(
                pallet_w, pallet_l, box_l, box_w
            )
            patterns["column_rotated"] = rotated

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

        # Stability metric combines COM, support, contact and vertical factors
        # -----------------------------------------------------------------
        # The layout's center of mass (COM) is compared with the pallet
        # center; large offsets reduce stability.  Layouts that extend
        # beyond the pallet bounds (overhang) lose stability in proportion
        # to the fraction of their area that is unsupported.  The metric also
        # considers how strongly cartons interlock (edge contact), how much
        # clearance remains to the pallet rim (edge buffer) and an estimated
        # vertical slenderness penalty derived from the carton height.
        if pattern:
            com_x = sum(x + w / 2 for x, _, w, _ in pattern) / len(pattern)
            com_y = sum(y + length / 2 for _, y, _, length in pattern) / len(pattern)
            center_x = self.pallet.width / 2
            center_y = self.pallet.length / 2
            dist = ((com_x - center_x) ** 2 + (com_y - center_y) ** 2) ** 0.5
            max_dist = max(1e-6, min(self.pallet.width, self.pallet.length) / 2)
            com_factor = max(0.0, 1 - dist / max_dist)

            total_inside = 0.0
            min_support_ratio = 1.0
            weakest_carton: Tuple[float, float, float, float] | None = None
            support_ratios: List[float] = []
            for x, y, w, length in pattern:
                overlap_w = max(0.0, min(x + w, self.pallet.width) - max(x, 0.0))
                overlap_l = max(0.0, min(y + length, self.pallet.length) - max(y, 0.0))
                supported_area = overlap_w * overlap_l
                total_inside += supported_area
                ratio = supported_area / box_area if box_area > 0 else 0.0
                support_ratios.append(ratio)
                if ratio < min_support_ratio:
                    min_support_ratio = ratio
                    weakest_carton = (x, y, w, length)
            if not support_ratios:
                min_support_ratio = 0.0
            if weakest_carton is None and pattern:
                weakest_carton = pattern[0]
            support_fraction = total_inside / (len(pattern) * box_area)
            weakest_support_ratio = min_support_ratio

            contact_fraction = self._edge_contact_fraction(pattern)
            buffer_score, min_clearance = self._edge_buffer_metrics(pattern)
            mix_ratio = self._orientation_mix(pattern)

            contact_factor = 0.4 + 0.6 * contact_fraction
            edge_factor = 0.6 + 0.4 * buffer_score

            contact_fraction = self._edge_contact_fraction(pattern)
            buffer_score = self._edge_buffer_score(pattern)
            mix_ratio = self._orientation_mix(pattern)

            contact_factor = 0.4 + 0.6 * contact_fraction
            edge_factor = 0.6 + 0.4 * buffer_score

            base_dim = max(1e-6, min(self.carton.width, self.carton.length))
            height_ratio = self.carton.height / base_dim if self.carton.height > 0 else 0.0
            vertical_factor = 1.0 / (1.0 + height_ratio / 2.0)

            gap_factor = max(0.2, 1.0 - (self.padding * 2.0) / max(base_dim, 1e-6))

            interlock_factor = 1.0 + 0.25 * mix_ratio

            stability = (
                com_factor
                * support_fraction
                * contact_factor
                * edge_factor
                * vertical_factor
                * gap_factor
                * interlock_factor
            )
            stability = max(0.0, min(1.0, stability))
            risk_reasons: List[str] = []
            if stability < RISK_STABILITY_THRESHOLD:
                risk_reasons.append("niska stabilność warstwy")
            if min_support_ratio < RISK_SUPPORT_THRESHOLD:
                risk_reasons.append("karton podparty w <50%")
            if contact_fraction < RISK_CONTACT_THRESHOLD:
                risk_reasons.append("słaby kontakt krawędziowy")
            if min_clearance < 0:
                risk_reasons.append("wystawanie poza obrys palety")
        else:
            stability = 0.0
            dist = 0.0
            support_fraction = 0.0
            min_support_ratio = 0.0
            weakest_carton = None
            weakest_support_ratio = 0.0
            contact_fraction = 0.0
            buffer_score = 0.0
            min_clearance = 0.0
            mix_ratio = 0.0
            risk_reasons = []
        grip_changes = 0
        score = PatternScore("", layer_eff, cube_eff, stability, grip_changes)
        score.carton_count = len(pattern)
        score.support_fraction = support_fraction
        score.min_support = min_support_ratio
        score.edge_contact = contact_fraction
        score.edge_buffer = buffer_score
        score.min_edge_clearance = min_clearance
        score.orientation_mix = mix_ratio
        score.com_offset = dist
        score.instability_risk = bool(risk_reasons)
        score.warnings = list(risk_reasons)
        score.weakest_carton = weakest_carton
        score.weakest_support = weakest_support_ratio
        return score

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
