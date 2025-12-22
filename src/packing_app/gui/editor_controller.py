from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot
from typing import Dict, Optional, Set, Tuple


@dataclass
class EditorController:
    selected_by_layer: Dict[int, Set[int]] = field(default_factory=lambda: {0: set(), 1: set()})
    active_layer: int | None = None
    drag_start: Optional[Tuple[float, float]] = None
    last_pos: Optional[Tuple[float, float]] = None
    is_dragging: bool = False
    drag_threshold_px: float = 4.0
    pressed_button: int | None = None

    def selection_for_layer(self, layer_idx: int) -> Set[int]:
        return self.selected_by_layer.setdefault(layer_idx, set())

    def set_selection_for_layer(self, layer_idx: int, selection: Set[int]) -> None:
        self.selected_by_layer[layer_idx] = set(selection)

    def set_selection_from_pairs(self, pairs: Set[Tuple[int, int]]) -> None:
        self.selected_by_layer = {}
        for layer_idx, idx in pairs:
            self.selected_by_layer.setdefault(layer_idx, set()).add(idx)

    def clear_all(self) -> None:
        for key in list(self.selected_by_layer.keys()):
            self.selected_by_layer[key].clear()

    def selected_pairs(self) -> Set[Tuple[int, int]]:
        return {
            (layer_idx, idx)
            for layer_idx, indices in self.selected_by_layer.items()
            for idx in indices
        }

    def on_press(
        self,
        layer_idx: int,
        hit_index: int | None,
        button: int,
        ctrl: bool,
        shift: bool,
        x: float,
        y: float,
    ) -> Dict[str, object]:
        selection_changed = False
        clear_layer = False
        self.active_layer = layer_idx

        layer_selection = self.selection_for_layer(layer_idx)

        if button == 1:
            if hit_index is None:
                if not ctrl and not shift:
                    if layer_selection:
                        layer_selection.clear()
                        selection_changed = True
                    clear_layer = True
            else:
                if ctrl or shift:
                    if hit_index in layer_selection:
                        layer_selection.remove(hit_index)
                    else:
                        layer_selection.add(hit_index)
                    selection_changed = True
                elif hit_index in layer_selection:
                    pass
                else:
                    layer_selection.clear()
                    layer_selection.add(hit_index)
                    selection_changed = True
        elif button == 3:
            if hit_index is not None:
                if hit_index in layer_selection:
                    pass
                elif not layer_selection:
                    layer_selection.add(hit_index)
                    selection_changed = True

        self.set_selection_for_layer(layer_idx, layer_selection)
        self.drag_start = (x, y)
        self.last_pos = (x, y)
        self.pressed_button = button
        self.is_dragging = False

        return {
            "selected": set(layer_selection),
            "selection_changed": selection_changed,
            "clear_layer": clear_layer,
        }

    def on_motion(self, x: float, y: float) -> Dict[str, object]:
        if self.pressed_button != 1:
            return {}
        if self.drag_start is None:
            return {}

        distance = hypot(x - self.drag_start[0], y - self.drag_start[1])
        if distance > self.drag_threshold_px:
            self.is_dragging = True

        delta: Optional[Tuple[float, float]] = None
        if self.is_dragging and self.last_pos is not None:
            delta = (x - self.last_pos[0], y - self.last_pos[1])

        self.last_pos = (x, y)

        if delta is None:
            return {}
        return {"delta": delta, "is_dragging": self.is_dragging}

    def on_release(self, button: int, x: float, y: float) -> Dict[str, object]:
        was_dragging = self.is_dragging
        self.drag_start = None
        self.last_pos = None
        self.is_dragging = False
        self.pressed_button = None
        return {"was_dragging": was_dragging}
