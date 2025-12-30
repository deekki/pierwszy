from __future__ import annotations

import json
import logging
import os
import re
import tkinter as tk
from dataclasses import dataclass, asdict
from tkinter import filedialog, messagebox, ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle

from palletizer_core.pally_export import (
    PallyExportConfig,
    build_pally_json,
    find_out_of_bounds,
    rects_to_pally_pattern,
)
from palletizer_core.signature import layout_signature
from packing_app.core.pallet_snapshot import PalletSnapshot

logger = logging.getLogger(__name__)


class TabURCaps(ttk.Frame):
    def __init__(self, parent, pallet_tab):
        super().__init__(parent)
        self.pallet_tab = pallet_tab
        self.active_snapshot: PalletSnapshot | None = None
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        self.pally_name_var = tk.StringVar(value="export")
        self.pally_out_dir_var = tk.StringVar(value=os.path.join(base_dir, "pally_exports"))
        self.pally_slip_vars: list[tk.BooleanVar] = []
        self.pally_label_orientation_map = {
            "Przód": 0,
            "Lewy bok": -90,
            "Prawy bok": 90,
            "Tył": 180,
        }
        self.pally_label_orientation_display_var = tk.StringVar(value="Tył")
        self.pally_swap_axes_var = tk.BooleanVar(value=False)
        self.left_palette_mode_var = tk.StringVar(value="mirror")
        self.approach_right_var = tk.StringVar(value="inverse")
        self.approach_left_var = tk.StringVar(value="inverse")
        self.placement_sequence_var = tk.StringVar(value="default")
        self.manual_mode_var = tk.BooleanVar(value=False)
        self.preview_side_var = tk.StringVar(value="right")
        self.manual_orders_by_signature: dict[str, list[int]] = {}
        self.manual_progress_by_signature: dict[str, int] = {}
        self.layer_signatures: list[str] = []
        self.signature_to_layers: dict[str, list[int]] = {}
        self.status_var = tk.StringVar(value="")
        self.snapshot_summary_var = tk.StringVar(value="Brak danych z Paletyzacji")
        self.weight_summary_var = tk.StringVar(value="Masa kartonu: -")
        self.preview_layer_var = tk.StringVar(value="1")
        self.manual_hint_var = tk.StringVar(value="")
        self.manual_move_target_var = tk.StringVar(value="")
        self.preview_boxes_info: list[tuple[int, tuple[float, float, float, float]]] = []
        self.current_preview_signature: str | None = None

        self.build_ui()

    def build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        main_frame = ttk.Frame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.columnconfigure(0, weight=1)

        fetch_frame = ttk.Frame(main_frame)
        fetch_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        fetch_frame.columnconfigure(1, weight=1)

        ttk.Button(
            fetch_frame,
            text="Pobierz z Paletyzacji",
            command=self.fetch_from_pallet,
        ).grid(row=0, column=0, padx=(0, 8), sticky="w")

        ttk.Label(fetch_frame, textvariable=self.snapshot_summary_var, justify="left").grid(
            row=0, column=1, sticky="w"
        )

        ttk.Label(fetch_frame, textvariable=self.weight_summary_var, justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )

        export_frame = ttk.LabelFrame(main_frame, text="Eksport UR CAPS")
        export_frame.grid(row=1, column=0, sticky="nsew")
        export_frame.columnconfigure(0, weight=1)

        header_frame = ttk.Frame(export_frame)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.columnconfigure(1, weight=1)

        ttk.Label(header_frame, text="Nazwa:").grid(row=0, column=0, padx=4, pady=4, sticky="e")
        ttk.Entry(header_frame, textvariable=self.pally_name_var, width=28).grid(
            row=0, column=1, padx=4, pady=4, sticky="ew"
        )

        ttk.Label(header_frame, text="Folder:").grid(row=1, column=0, padx=4, pady=4, sticky="e")
        folder_frame = ttk.Frame(header_frame)
        folder_frame.grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        folder_frame.columnconfigure(0, weight=1)
        ttk.Entry(folder_frame, textvariable=self.pally_out_dir_var).grid(
            row=0, column=0, padx=(0, 4), sticky="ew"
        )
        ttk.Button(folder_frame, text="...", width=3, command=self._choose_directory).grid(
            row=0, column=1
        )

        pattern_frame = ttk.Frame(header_frame)
        pattern_frame.grid(row=2, column=0, columnspan=2, padx=4, pady=4, sticky="w")
        ttk.Button(pattern_frame, text="Zapisz wzór", command=self._save_pattern).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(pattern_frame, text="Wczytaj wzór", command=self._load_pattern).pack(
            side=tk.LEFT
        )

        basic_frame = ttk.LabelFrame(export_frame, text="BASIC")
        basic_frame.grid(row=1, column=0, sticky="ew", padx=4, pady=(4, 8))
        basic_frame.columnconfigure(1, weight=1)

        ttk.Label(basic_frame, text="Kierunek etykiety:").grid(
            row=0, column=0, padx=4, pady=4, sticky="e"
        )
        ttk.Combobox(
            basic_frame,
            textvariable=self.pally_label_orientation_display_var,
            values=list(self.pally_label_orientation_map.keys()),
            state="readonly",
            width=25,
        ).grid(row=0, column=1, padx=4, pady=4, sticky="w")

        ttk.Label(basic_frame, text="Lewa paleta:").grid(
            row=1, column=0, padx=4, pady=4, sticky="e"
        )
        ttk.Combobox(
            basic_frame,
            textvariable=self.left_palette_mode_var,
            values=["mirror", "altPattern"],
            state="readonly",
            width=25,
        ).grid(row=1, column=1, padx=4, pady=4, sticky="w")

        ttk.Label(basic_frame, text="Approach (prawa):").grid(
            row=2, column=0, padx=4, pady=4, sticky="e"
        )
        ttk.Combobox(
            basic_frame,
            textvariable=self.approach_right_var,
            values=["normal", "inverse"],
            state="readonly",
            width=25,
        ).grid(row=2, column=1, padx=4, pady=4, sticky="w")

        ttk.Label(basic_frame, text="Approach (lewa):").grid(
            row=3, column=0, padx=4, pady=4, sticky="e"
        )
        ttk.Combobox(
            basic_frame,
            textvariable=self.approach_left_var,
            values=["normal", "inverse"],
            state="readonly",
            width=25,
        ).grid(row=3, column=1, padx=4, pady=4, sticky="w")

        ttk.Label(
            basic_frame,
            text=(
                "approach dotyczy prawej palety, altApproach lewej; normal/inverse "
                "zmienia kierunek budowy warstwy i kolejność odkładania"
            ),
            wraplength=360,
            justify="left",
        ).grid(row=4, column=0, columnspan=2, padx=4, pady=(0, 4), sticky="w")

        ttk.Checkbutton(
            basic_frame,
            text="Swap axes for PALLY (EUR)",
            variable=self.pally_swap_axes_var,
        ).grid(row=5, column=0, columnspan=2, padx=4, pady=4, sticky="w")

        ttk.Label(basic_frame, text="Przekładka po warstwie:").grid(
            row=6, column=0, padx=4, pady=4, sticky="ne"
        )
        self.pally_slip_frame = ttk.Frame(basic_frame)
        self.pally_slip_frame.grid(row=6, column=1, padx=4, pady=4, sticky="w")

        ttk.Button(
            export_frame,
            text="Eksportuj PALLY JSON",
            command=self.export_pally_json,
        ).grid(row=2, column=0, padx=4, pady=(8, 4), sticky="ew")

        ttk.Label(export_frame, textvariable=self.status_var, justify="left").grid(
            row=3, column=0, padx=4, pady=(2, 0), sticky="w"
        )

        preview_frame = ttk.LabelFrame(main_frame, text="Podgląd warstwy")
        preview_frame.grid(row=2, column=0, sticky="nsew", pady=(8, 0))
        preview_frame.columnconfigure(0, weight=3)
        preview_frame.columnconfigure(1, weight=2)
        preview_frame.rowconfigure(1, weight=1)

        controls_frame = ttk.Frame(preview_frame)
        controls_frame.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        controls_frame.columnconfigure(1, weight=1)

        ttk.Label(controls_frame, text="Warstwa:").grid(
            row=0, column=0, padx=4, pady=4, sticky="e"
        )
        self.preview_layer_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.preview_layer_var,
            state="readonly",
            width=10,
        )
        self.preview_layer_combo.grid(row=0, column=1, padx=4, pady=4, sticky="w")
        self.preview_layer_combo.bind("<<ComboboxSelected>>", self._render_layer_preview)

        ttk.Label(controls_frame, text="Podgląd palety:").grid(
            row=0, column=2, padx=4, pady=4, sticky="e"
        )
        ttk.Radiobutton(
            controls_frame,
            text="Prawa",
            value="right",
            variable=self.preview_side_var,
            command=self._render_layer_preview,
        ).grid(row=0, column=3, padx=2, pady=4, sticky="w")
        ttk.Radiobutton(
            controls_frame,
            text="Lewa",
            value="left",
            variable=self.preview_side_var,
            command=self._render_layer_preview,
        ).grid(row=0, column=4, padx=2, pady=4, sticky="w")

        canvas_frame = ttk.Frame(preview_frame)
        canvas_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        self.preview_fig = plt.Figure(figsize=(6, 3.5))
        self.preview_ax = self.preview_fig.add_subplot(111)
        self.preview_canvas = FigureCanvasTkAgg(self.preview_fig, master=canvas_frame)
        self.preview_canvas.get_tk_widget().grid(
            row=0, column=0, sticky="nsew"
        )
        self.preview_canvas.mpl_connect("button_press_event", self._on_canvas_click)

        manual_frame = ttk.LabelFrame(preview_frame, text="Tryb ręczny")
        manual_frame.grid(row=1, column=1, sticky="nsew", padx=4, pady=(0, 4))
        manual_frame.columnconfigure(0, weight=1)

        mode_row = ttk.Frame(manual_frame)
        mode_row.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Checkbutton(
            mode_row,
            text="Tryb ręczny",
            variable=self.manual_mode_var,
            command=self._on_manual_mode_toggle,
        ).grid(row=0, column=0, padx=(0, 8), sticky="w")
        ttk.Button(
            mode_row,
            text="Reset do auto",
            command=self._reset_manual_order,
        ).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(
            mode_row,
            text="Odwróć kolejność",
            command=self._reverse_manual_order,
        ).grid(row=0, column=2, padx=(0, 6))

        self.manual_hint_label = ttk.Label(
            manual_frame,
            textvariable=self.manual_hint_var,
            wraplength=220,
            justify="left",
        )
        self.manual_hint_label.grid(row=1, column=0, sticky="w", pady=(0, 6))

        self.order_tree = ttk.Treeview(
            manual_frame,
            columns=("pozycja",),
            show="headings",
            selectmode="browse",
            height=8,
        )
        self.order_tree.heading("pozycja", text="Kolejność")
        self.order_tree.column("pozycja", width=80, anchor="center")
        self.order_tree.grid(row=2, column=0, sticky="nsew")

        controls_row = ttk.Frame(manual_frame)
        controls_row.grid(row=3, column=0, sticky="ew", pady=6)
        controls_row.columnconfigure(2, weight=1)
        ttk.Button(controls_row, text="Góra", command=self._move_selected_up).grid(
            row=0, column=0, padx=2
        )
        ttk.Button(controls_row, text="Dół", command=self._move_selected_down).grid(
            row=0, column=1, padx=2
        )
        ttk.Entry(controls_row, textvariable=self.manual_move_target_var, width=6).grid(
            row=0, column=2, padx=2, sticky="w"
        )
        ttk.Button(controls_row, text="Przenieś", command=self._move_selected_to).grid(
            row=0, column=3, padx=2
        )

        manual_frame.rowconfigure(2, weight=1)

        self._draw_empty_preview("Brak danych do podglądu")
        self._bind_preview_traces()

    def _save_pattern(self) -> None:
        if not self.pallet_tab:
            messagebox.showwarning("UR CAPS", "Brak zakładki Paletyzacja.")
            return
        try:
            self.pallet_tab.save_pattern_dialog()
        except Exception:
            logger.exception("Failed to save pattern from UR CAPS")

    def _load_pattern(self) -> None:
        if not self.pallet_tab:
            messagebox.showwarning("UR CAPS", "Brak zakładki Paletyzacja.")
            return
        try:
            self.pallet_tab.load_pattern_dialog()
            inputs = getattr(self.pallet_tab, "_read_inputs", None)
            updater = getattr(self.pallet_tab, "_update_snapshot", None)
            if callable(inputs) and callable(updater):
                updater(inputs())
            self.fetch_from_pallet(quiet_if_missing=True)
        except Exception:
            logger.exception("Failed to load pattern from UR CAPS")

    def fetch_from_pallet(self, quiet_if_missing: bool = False) -> None:
        snapshot = getattr(self.pallet_tab, "last_snapshot", None)
        if snapshot is None:
            message = "Brak zapisanego układu w zakładce Paletyzacja."
            if quiet_if_missing:
                self.status_var.set(message)
                return
            messagebox.showinfo("UR CAPS", message)
            return
        self.apply_snapshot(snapshot)

    def apply_snapshot(self, snapshot: PalletSnapshot) -> None:
        self.active_snapshot = snapshot
        self.manual_orders_by_signature.clear()
        self.manual_progress_by_signature.clear()
        self.layer_signatures = []
        self.signature_to_layers = {}
        self._update_snapshot_summary(snapshot)
        self._update_slip_checkboxes(snapshot.num_layers or len(snapshot.layers))
        for idx, var in enumerate(self.pally_slip_vars):
            if idx and idx in snapshot.slips_after:
                var.set(True)
        self.pally_swap_axes_var.set(snapshot.pallet_w > snapshot.pallet_l)
        self.status_var.set("Pobrano dane z Paletyzacji")
        self._update_weight_summary()
        self._refresh_preview_layers(len(snapshot.layers))
        self._render_layer_preview()

    def _update_snapshot_summary(self, snapshot: PalletSnapshot) -> None:
        pallet = f"Paleta: {snapshot.pallet_w} × {snapshot.pallet_l} × {snapshot.pallet_h} mm"
        box = f"Karton: {snapshot.box_w} × {snapshot.box_l} × {snapshot.box_h} mm"
        layers = f"Warstwy: {len(snapshot.layers)}"
        self.snapshot_summary_var.set(f"{pallet} | {box} | {layers}")

    def _update_weight_summary(self) -> None:
        weight_g, source = self._get_box_weight_g()
        if weight_g:
            source_label = "ręcznie" if source == "manual" else "katalog"
            self.weight_summary_var.set(
                f"Masa kartonu: {weight_g / 1000:.3f} kg ({source_label})"
            )
        else:
            self.weight_summary_var.set("Masa kartonu: brak danych")

    def _update_slip_checkboxes(self, layer_count: int) -> None:
        for widget in self.pally_slip_frame.winfo_children():
            widget.destroy()
        self.pally_slip_vars.clear()
        base_var = tk.BooleanVar(value=True)
        self.pally_slip_vars.append(base_var)
        ttk.Checkbutton(
            self.pally_slip_frame,
            text="0",
            variable=base_var,
        ).grid(row=0, column=0, padx=2, pady=0, sticky="w")

        for idx in range(1, layer_count + 1):
            var = tk.BooleanVar(value=False)
            self.pally_slip_vars.append(var)
            ttk.Checkbutton(
                self.pally_slip_frame,
                text=str(idx),
                variable=var,
            ).grid(row=0, column=idx, padx=2, pady=0, sticky="w")

    def _selected_slip_layers(self) -> set[int]:
        slips: set[int] = set()
        for idx, var in enumerate(self.pally_slip_vars):
            if idx == 0:
                continue
            if var.get():
                slips.add(idx)
        return slips

    @staticmethod
    def _slugify_filename(value: str) -> str:
        slug = re.sub(r"[^\w\-]+", "_", value.strip().lower())
        slug = slug.strip("_")
        return slug or "export"

    def _bind_preview_traces(self) -> None:
        for var in (
            self.pally_label_orientation_display_var,
            self.pally_swap_axes_var,
            self.approach_left_var,
            self.approach_right_var,
            self.preview_side_var,
        ):
            var.trace_add("write", self._render_layer_preview)

    def _manual_mode_enabled(self) -> bool:
        return bool(self.manual_mode_var.get())

    def _on_manual_mode_toggle(self) -> None:
        snapshot = self.active_snapshot
        if snapshot and self._manual_mode_enabled():
            layer_idx = self._selected_layer_index(len(snapshot.layer_rects_list))
            signature = self._current_signature(layer_idx)
            if signature:
                self._ensure_manual_order_for_signature(
                    signature, len(snapshot.layer_rects_list[layer_idx - 1])
                )
        self._render_layer_preview()

    def _current_signature(self, layer_idx: int) -> str | None:
        if not self.layer_signatures or layer_idx - 1 >= len(self.layer_signatures):
            return None
        return self.layer_signatures[layer_idx - 1]

    def _ensure_manual_order_for_signature(self, signature: str, rect_count: int) -> list[int]:
        order = self.manual_orders_by_signature.get(signature)
        if not order or len(order) != rect_count:
            order = list(range(rect_count))
            self.manual_orders_by_signature[signature] = order
            self.manual_progress_by_signature[signature] = 0
        else:
            self.manual_progress_by_signature.setdefault(signature, rect_count)
        return order

    def _manual_orders_payload(self, snapshot: PalletSnapshot) -> dict[str, list[int]] | None:
        if not self._manual_mode_enabled():
            return None
        orders: dict[str, list[int]] = {}
        for idx, rects in enumerate(snapshot.layer_rects_list, start=1):
            signature = self._current_signature(idx)
            if not signature:
                continue
            orders[signature] = list(
                self._ensure_manual_order_for_signature(signature, len(rects))
            )
        return orders

    def _update_manual_hint(self, signature: str | None, layer_idx: int) -> None:
        if not signature:
            self.manual_hint_var.set("")
            return
        layers = self.signature_to_layers.get(signature, [])
        if len(layers) > 1:
            self.manual_hint_var.set(
                "Edycja dotyczy warstw o tym samym układzie: "
                + ", ".join(map(str, layers))
            )
        else:
            self.manual_hint_var.set("")

    def _update_signature_context(self, snapshot: PalletSnapshot, config: PallyExportConfig) -> None:
        swap_axes = bool(config.swap_axes_for_pally)
        pallet_width = min(config.pallet_w, config.pallet_l) if swap_axes else config.pallet_w
        pallet_length = max(config.pallet_w, config.pallet_l) if swap_axes else config.pallet_l
        carton_w = config.box_l if swap_axes else config.box_w
        carton_l = config.box_w if swap_axes else config.box_l

        signatures: list[str] = []
        signature_to_layers: dict[str, list[int]] = {}
        for idx, rects in enumerate(snapshot.layer_rects_list, start=1):
            rects_to_use = [(y, x, length, w) for x, y, w, length in rects] if swap_axes else rects
            _, signature_rects = rects_to_pally_pattern(
                rects_to_use,
                carton_w,
                carton_l,
                pallet_width,
                pallet_length,
                quant_step_mm=config.quant_step_mm,
                label_orientation=config.label_orientation,
                placement_sequence=config.placement_sequence,
            )
            signature_value = layout_signature(
                signature_rects, eps=config.signature_eps_mm
            )
            signature_str = str(signature_value)
            signatures.append(signature_str)
            signature_to_layers.setdefault(signature_str, []).append(idx)

        self.layer_signatures = signatures
        self.signature_to_layers = signature_to_layers

    def _refresh_order_tree(self, order: list[int]) -> None:
        for item in self.order_tree.get_children():
            self.order_tree.delete(item)
        for idx, _ in enumerate(order, start=1):
            self.order_tree.insert("", "end", values=(idx,))
        if self._manual_mode_enabled():
            self.order_tree.state(("!disabled",))
            self.manual_hint_label.state(("!disabled",))
        else:
            self.order_tree.state(("disabled",))
            self.manual_hint_label.state(("disabled",))

    def _move_selected_up(self) -> None:
        self._move_selected(delta=-1)

    def _move_selected_down(self) -> None:
        self._move_selected(delta=1)

    def _move_selected(self, delta: int) -> None:
        if not self._manual_mode_enabled():
            return
        snapshot = self.active_snapshot
        if snapshot is None:
            return
        layer_idx = self._selected_layer_index(len(snapshot.layer_rects_list))
        signature = self._current_signature(layer_idx)
        if not signature:
            return
        order = self._ensure_manual_order_for_signature(
            signature, len(snapshot.layer_rects_list[layer_idx - 1])
        )
        selection = self.order_tree.selection()
        if not selection:
            return
        selected_index = self.order_tree.index(selection[0])
        target = selected_index + delta
        if target < 0 or target >= len(order):
            return
        value = order.pop(selected_index)
        order.insert(target, value)
        self.manual_orders_by_signature[signature] = order
        self.manual_progress_by_signature[signature] = len(order)
        self._render_layer_preview()

    def _move_selected_to(self) -> None:
        if not self._manual_mode_enabled():
            return
        snapshot = self.active_snapshot
        if snapshot is None:
            return
        layer_idx = self._selected_layer_index(len(snapshot.layer_rects_list))
        signature = self._current_signature(layer_idx)
        if not signature:
            return
        order = self._ensure_manual_order_for_signature(
            signature, len(snapshot.layer_rects_list[layer_idx - 1])
        )
        selection = self.order_tree.selection()
        if not selection:
            return
        try:
            target = int(self.manual_move_target_var.get()) - 1
        except (TypeError, ValueError):
            return
        if target < 0 or target >= len(order):
            return
        selected_index = self.order_tree.index(selection[0])
        value = order.pop(selected_index)
        order.insert(target, value)
        self.manual_orders_by_signature[signature] = order
        self.manual_progress_by_signature[signature] = len(order)
        self._render_layer_preview()

    def _reverse_manual_order(self) -> None:
        if not self._manual_mode_enabled():
            return
        snapshot = self.active_snapshot
        if snapshot is None:
            return
        layer_idx = self._selected_layer_index(len(snapshot.layer_rects_list))
        signature = self._current_signature(layer_idx)
        if not signature:
            return
        order = self._ensure_manual_order_for_signature(
            signature, len(snapshot.layer_rects_list[layer_idx - 1])
        )
        order.reverse()
        self.manual_orders_by_signature[signature] = order
        self.manual_progress_by_signature[signature] = len(order)
        self._render_layer_preview()

    def _reset_manual_order(self) -> None:
        snapshot = self.active_snapshot
        if snapshot is None:
            return
        layer_idx = self._selected_layer_index(len(snapshot.layer_rects_list))
        signature = self._current_signature(layer_idx)
        if not signature:
            return
        rect_count = len(snapshot.layer_rects_list[layer_idx - 1])
        self.manual_orders_by_signature[signature] = list(range(rect_count))
        self.manual_progress_by_signature[signature] = 0
        self._render_layer_preview()

    def _collect_config(self) -> URCapsConfig:
        return URCapsConfig(
            name=self.pally_name_var.get().strip() or "export",
            output_dir=self.pally_out_dir_var.get().strip(),
            label_orientation_display=self.pally_label_orientation_display_var.get(),
            swap_axes_for_pally=bool(self.pally_swap_axes_var.get()),
            slips_after=self._selected_slip_layers(),
            left_palette_mode=self.left_palette_mode_var.get(),
            approach_right=self.approach_right_var.get(),
            approach_left=self.approach_left_var.get(),
            placement_sequence=self.placement_sequence_var.get(),
        )

    def _make_pally_config(
        self, snapshot: PalletSnapshot, ur_config: URCapsConfig, *, name_override: str | None = None
    ) -> PallyExportConfig:
        box_weight_g, _ = self._get_box_weight_g()
        return PallyExportConfig(
            name=name_override or ur_config.name,
            pallet_w=int(round(snapshot.pallet_w)),
            pallet_l=int(round(snapshot.pallet_l)),
            pallet_h=int(round(snapshot.pallet_h)),
            box_w=int(round(snapshot.box_w + 2 * snapshot.thickness)),
            box_l=int(round(snapshot.box_l + 2 * snapshot.thickness)),
            box_h=int(round(snapshot.box_h + 2 * snapshot.thickness)),
            box_weight_g=box_weight_g,
            overhang_ends=0,
            overhang_sides=0,
            label_orientation=self.pally_label_orientation_map.get(
                ur_config.label_orientation_display, 180
            ),
            swap_axes_for_pally=bool(ur_config.swap_axes_for_pally),
            alt_layout=ur_config.left_palette_mode,
            approach=ur_config.approach_right,
            alt_approach=ur_config.approach_left,
            placement_sequence=ur_config.placement_sequence,
        )

    def _choose_directory(self) -> None:
        path = filedialog.askdirectory(initialdir=self.pally_out_dir_var.get())
        if path:
            self.pally_out_dir_var.set(path)

    def _get_box_weight_g(self) -> tuple[int, str]:
        if hasattr(self.pallet_tab, "_get_active_carton_weight"):
            weight_kg, source = self.pallet_tab._get_active_carton_weight()  # pylint: disable=protected-access
            return int(round(max(weight_kg, 0.0) * 1000)), source
        return 0, "unknown"

    def _refresh_preview_layers(self, layer_count: int) -> None:
        values = [str(idx) for idx in range(1, layer_count + 1)]
        self.preview_layer_combo["values"] = values
        if values:
            if self.preview_layer_var.get() not in values:
                self.preview_layer_var.set(values[0])
        else:
            self.preview_layer_var.set("1")

    def _selected_layer_index(self, max_layers: int) -> int:
        try:
            selected = int(self.preview_layer_var.get())
        except (TypeError, ValueError):
            return 1
        return min(max(selected, 1), max_layers)

    def _build_preview_payload(self, snapshot: PalletSnapshot) -> dict | None:
        if not snapshot.layer_rects_list:
            return None

        ur_config = self._collect_config()
        config = self._make_pally_config(snapshot, ur_config, name_override="preview")
        self._update_signature_context(snapshot, config)
        manual_orders = self._manual_orders_payload(snapshot)

        return build_pally_json(
            config=config,
            layer_rects_list=snapshot.layer_rects_list,
            slips_after=self._selected_slip_layers(),
            include_base_slip=(
                bool(self.pally_slip_vars[0].get()) if self.pally_slip_vars else True
            ),
            manual_orders_by_signature=manual_orders,
        )

    def _extract_layer_pattern(self, payload: dict, layer_idx: int) -> list[dict] | None:
        layer_types = {lt.get("name"): lt for lt in payload.get("layerTypes", [])}
        layer_counter = 0
        for layer_name in payload.get("layers", []):
            layer_type = layer_types.get(layer_name)
            if not layer_type or layer_type.get("class") == "separator":
                continue
            layer_counter += 1
            if layer_counter == layer_idx:
                return layer_type.get("pattern") or []
        return None

    def _draw_empty_preview(self, message: str) -> None:
        self.preview_ax.clear()
        self.preview_ax.axis("off")
        self.preview_boxes_info = []
        self.current_preview_signature = None
        self.preview_ax.text(
            0.5,
            0.5,
            message,
            ha="center",
            va="center",
            transform=self.preview_ax.transAxes,
        )
        self.preview_canvas.draw()

    def _draw_layer_pattern(
        self,
        payload: dict,
        pattern: list[dict],
        layer_idx: int,
        approach: str,
        side: str,
    ) -> None:
        dimensions = payload.get("dimensions", {})
        product_dims = payload.get("productDimensions", {})
        pallet_w = float(dimensions.get("width", 0))
        pallet_l = float(dimensions.get("length", 0))
        product_w = float(product_dims.get("width", 0))
        product_l = float(product_dims.get("length", 0))

        if not pallet_w or not pallet_l or not product_w or not product_l:
            self._draw_empty_preview("Brak danych do podglądu")
            return

        self.preview_ax.clear()
        side_label = "prawa" if self.preview_side_var.get() == "right" else "lewa"
        self.preview_ax.set_title(f"Warstwa {layer_idx} ({side_label})")
        self.preview_ax.set_aspect("equal")
        self.preview_ax.add_patch(
            Rectangle((0, 0), pallet_w, pallet_l, fill=False, edgecolor="black", lw=1.5)
        )

        centers: list[tuple[float, float]] = []
        boxes: list[tuple[int, tuple[float, float, float, float]]] = []
        for idx, item in enumerate(pattern, start=1):
            rotation = (item.get("r") or [0])[0]
            width, length = (
                (product_w, product_l) if rotation in (0, 180) else (product_l, product_w)
            )
            x_center = float(item.get("x", 0))
            y_center = float(item.get("y", 0))
            x_left = x_center - width / 2.0
            y_bottom = y_center - length / 2.0
            boxes.append((idx - 1, (x_left, x_left + width, y_bottom, y_bottom + length)))
            self.preview_ax.add_patch(
                Rectangle(
                    (x_left, y_bottom),
                    width,
                    length,
                    fill=True,
                    facecolor="#cfe2f3",
                    edgecolor="#0b5394",
                    lw=1,
                    alpha=0.9,
                )
            )
            self.preview_ax.text(
                x_center,
                y_center,
                str(idx),
                ha="center",
                va="center",
                fontsize=9,
                color="#0b5394",
                fontweight="bold",
            )
            if centers:
                self.preview_ax.annotate(
                    "",
                    xy=(x_center, y_center),
                    xytext=centers[-1],
                    arrowprops={"arrowstyle": "->", "color": "#cc0000", "lw": 1.2},
                )
            centers.append((x_center, y_center))

        self.preview_boxes_info = boxes

        self.preview_ax.set_xlim(
            0, max(pallet_w, max((c[0] for c in centers), default=0))
        )
        self.preview_ax.set_ylim(
            0, max(pallet_l, max((c[1] for c in centers), default=0))
        )
        self.preview_ax.grid(True, linestyle="--", alpha=0.2)
        self.preview_ax.set_xlabel("Szerokość [mm]")
        self.preview_ax.set_ylabel("Długość [mm]")
        self._draw_approach_arrow(pallet_w, pallet_l, approach, side)
        self.preview_canvas.draw()

    def _draw_approach_arrow(
        self, pallet_w: float, pallet_l: float, approach: str, side: str
    ) -> None:
        arrow_color = "#7f3fbf"
        is_inverse = approach == "inverse"
        if is_inverse:
            start_y, end_y = pallet_l * 0.85, pallet_l * 0.15
        else:
            start_y, end_y = pallet_l * 0.15, pallet_l * 0.85
        margin = pallet_w * 0.08
        x = pallet_w - margin if side == "right" else margin
        self.preview_ax.annotate(
            "",
            xy=(x, end_y),
            xytext=(x, start_y),
            arrowprops={"arrowstyle": "simple", "color": arrow_color, "alpha": 0.4},
        )
        self.preview_ax.text(
            x,
            (start_y + end_y) / 2,
            f"{side.upper()} | {approach}",
            ha="right" if side == "right" else "left",
            va="center",
            color=arrow_color,
            fontsize=9,
        )

    def _box_index_from_event(self, x: float | None, y: float | None) -> int | None:
        if x is None or y is None:
            return None
        for idx, (x_left, x_right, y_bottom, y_top) in self.preview_boxes_info:
            if x_left <= x <= x_right and y_bottom <= y <= y_top:
                return idx
        return None

    def _on_canvas_click(self, event) -> None:  # noqa: ANN001
        if not self._manual_mode_enabled() or event.inaxes != self.preview_ax:
            return
        snapshot = self.active_snapshot
        signature = self.current_preview_signature
        if snapshot is None or not signature:
            return
        layer_idx = self._selected_layer_index(len(snapshot.layer_rects_list))
        rect_count = len(snapshot.layer_rects_list[layer_idx - 1])
        order = self._ensure_manual_order_for_signature(signature, rect_count)
        progress = self.manual_progress_by_signature.get(signature, 0)

        box_idx = self._box_index_from_event(event.xdata, event.ydata)
        if box_idx is None:
            return

        if event.button == 1:
            if box_idx in order[:progress]:
                return
            if box_idx in order:
                order.remove(box_idx)
            order.insert(progress, box_idx)
            progress = min(progress + 1, len(order))
        elif event.button == 3:
            if progress > 0:
                removed = order.pop(progress - 1)
                order.append(removed)
                progress -= 1
            else:
                order[:] = list(range(len(order)))
                progress = 0
        else:
            return

        self.manual_orders_by_signature[signature] = order
        self.manual_progress_by_signature[signature] = progress
        self._render_layer_preview()

    def _render_layer_preview(self, *args) -> None:  # noqa: ARG002
        snapshot = self.active_snapshot
        if snapshot is None or not snapshot.layer_rects_list:
            self._draw_empty_preview("Brak danych do podglądu")
            return

        layer_idx = self._selected_layer_index(len(snapshot.layer_rects_list))
        payload = self._build_preview_payload(snapshot)
        if not payload:
            self._draw_empty_preview("Brak danych do podglądu")
            return

        pattern = self._extract_layer_pattern(payload, layer_idx)
        if not pattern:
            self._draw_empty_preview("Brak wzoru warstwy")
            return

        signature = self._current_signature(layer_idx)
        self.current_preview_signature = signature
        self._update_manual_hint(signature, layer_idx)

        if self._manual_mode_enabled() and signature:
            order = self._ensure_manual_order_for_signature(
                signature, len(pattern)
            )
        else:
            order = list(range(len(pattern)))
        self._refresh_order_tree(order)

        side = self.preview_side_var.get()
        approach = (
            self.approach_right_var.get()
            if side == "right"
            else self.approach_left_var.get()
        )

        try:
            self._draw_layer_pattern(payload, pattern, layer_idx, approach, side)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to draw UR CAPS layer preview")
            self._draw_empty_preview("Błąd podglądu")

    def export_pally_json(self) -> None:
        snapshot = self.active_snapshot
        if snapshot is None:
            messagebox.showwarning("UR CAPS", "Brak danych do eksportu.")
            return
        if not snapshot.layers:
            messagebox.showwarning("UR CAPS", "Brak warstw do eksportu.")
            return

        ur_config = self._collect_config()
        if not ur_config.output_dir:
            messagebox.showwarning("Brak folderu", "Podaj folder zapisu.")
            return

        box_weight_g, _ = self._get_box_weight_g()
        if not box_weight_g:
            messagebox.showwarning(
                "Brak masy",
                "Brak masy kartonu. Uzupełnij pole w zakładce Paletyzacja.",
            )
            return

        layer_rects_list = snapshot.layer_rects_list
        if not layer_rects_list:
            messagebox.showwarning("UR CAPS", "Brak współrzędnych warstw w snapshot.")
            return

        config = self._make_pally_config(snapshot, ur_config)
        self._update_signature_context(snapshot, config)
        manual_orders = self._manual_orders_payload(snapshot)

        payload = build_pally_json(
            config=config,
            layer_rects_list=layer_rects_list,
            slips_after=ur_config.slips_after,
            include_base_slip=bool(self.pally_slip_vars[0].get()) if self.pally_slip_vars else True,
            manual_orders_by_signature=manual_orders,
        )

        warnings = find_out_of_bounds(payload)
        if warnings:
            self.status_var.set(f"Błąd: {warnings[0]}")
            return

        os.makedirs(ur_config.output_dir, exist_ok=True)
        filename = f"{self._slugify_filename(ur_config.name)}.json"
        path = os.path.join(ur_config.output_dir, filename)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=4, ensure_ascii=False)
        self.status_var.set(f"Zapisano PALLY JSON: {path}")

@dataclass
class URCapsConfig:
    name: str
    output_dir: str
    label_orientation_display: str
    swap_axes_for_pally: bool
    slips_after: set[int]
    left_palette_mode: str = "mirror"
    approach_right: str = "inverse"
    approach_left: str = "inverse"
    placement_sequence: str = "default"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["slips_after"] = sorted(self.slips_after)
        return data
