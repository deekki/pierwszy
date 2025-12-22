from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot
from typing import Dict, Optional, Set, Tuple


@dataclass
class EditorState:
    selected: Set[int] = field(default_factory=set)
    active_index: int | None = None
    drag_start: Optional[Tuple[float, float]] = None
    last_pos: Optional[Tuple[float, float]] = None
    is_dragging: bool = False
    drag_threshold_px: float = 4.0
    pressed_button: int | None = None

    def on_press(
        self,
        hit_index: int | None,
        button: int,
        ctrl: bool,
        shift: bool,
        x: float,
        y: float,
    ) -> Dict[str, object]:
        selection_changed = False
        clear_all = False

        if button == 1:
            if hit_index is None:
                if not ctrl and not shift:
                    self.selected = set()
                    selection_changed = True
                    clear_all = True
            elif hit_index in self.selected:
                pass
            else:
                if ctrl or shift:
                    if hit_index in self.selected:
                        self.selected.remove(hit_index)
                    else:
                        self.selected.add(hit_index)
                else:
                    self.selected = {hit_index}
                selection_changed = True
        elif button == 3:
            if hit_index is not None:
                if hit_index in self.selected:
                    pass
                elif not self.selected:
                    self.selected = {hit_index}
                    selection_changed = True

        self.active_index = hit_index if button == 1 else None
        self.drag_start = (x, y)
        self.last_pos = (x, y)
        self.pressed_button = button
        self.is_dragging = False

        return {
            "selected": set(self.selected),
            "selection_changed": selection_changed,
            "clear_all": clear_all,
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
        self.active_index = None
        return {"was_dragging": was_dragging}
