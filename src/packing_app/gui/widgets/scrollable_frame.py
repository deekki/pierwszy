from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ScrollableFrame(ttk.Frame):
    def __init__(self, parent: tk.Widget, **kwargs):
        super().__init__(parent, **kwargs)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.vscrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vscrollbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vscrollbar.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.interior = ttk.Frame(self.canvas)
        self.interior_id = self.canvas.create_window((0, 0), window=self.interior, anchor="nw")

        self.interior.bind("<Configure>", self._on_interior_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self._bind_mousewheel(self.canvas)
        self._bind_mousewheel(self.interior)

    def _on_interior_configure(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        canvas_width = event.width
        self.canvas.itemconfigure(self.interior_id, width=canvas_width)

    def _on_mousewheel(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if event.delta == 0:
            return
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind_mousewheel(self, widget: tk.Widget) -> None:
        widget.bind_all("<MouseWheel>", self._on_mousewheel, add=True)
        widget.bind_all("<Shift-MouseWheel>", self._on_mousewheel, add=True)
