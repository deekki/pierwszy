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
from matplotlib.patches import Circle, Rectangle

from palletizer_core.pally_export import (
    PallyExportConfig,
    build_pally_json,
    find_out_of_bounds,
    mirror_pattern,
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
        self.box_weight_override_var = tk.StringVar(value="")
        self.slip_summary_var = tk.StringVar(value="Przekładki (eksport): -")
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
        self.manual_edit_target_var = tk.StringVar(value="both")
        self.manual_orders: dict[str, dict[str, list[int]]] = {}
        self.layer_signatures: list[str] = []
        self.signature_to_layers: dict[str, list[int]] = {}
        self.status_var = tk.StringVar(value="")
        self.snapshot_summary_var = tk.StringVar(value="Brak danych z Paletyzacji")
        self.weight_summary_var = tk.StringVar(value="Masa kartonu: -")
        self.preview_layer_var = tk.StringVar(value="1")
        self.manual_hint_var = tk.StringVar(value="")
        self.current_preview_signature: str | None = None
        self.preview_overlay_artists: list = []
        self.loaded_payload: dict | None = None
        self.pallet_height_override_var = tk.StringVar(value="")
        self.dimensions_height_override_var = tk.StringVar(value="")
        self.pretty_json_var = tk.BooleanVar(value=True)
        self.omit_altpattern_when_mirror_var = tk.BooleanVar(value=False)
        self.manual_sync_parity_var = tk.BooleanVar(value=False)
        self.box_weight_override_var.trace_add("write", self._on_weight_override_changed)
        self.manual_sync_parity_var.trace_add("write", self._on_manual_sync_parity_toggle)

        self.build_ui()

    def build_ui(self) -> None:
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        main_frame = ttk.Frame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=0)
        main_frame.rowconfigure(1, weight=0)
        main_frame.rowconfigure(2, weight=1)

        fetch_frame = ttk.Frame(main_frame)
        fetch_frame.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        fetch_frame.columnconfigure(1, weight=1)

        ttk.Button(
            fetch_frame,
            text="Pobierz z Paletyzacji",
            command=self.fetch_from_pallet,
        ).grid(row=0, column=0, padx=(0, 8), sticky="w")

        ttk.Label(fetch_frame, textvariable=self.snapshot_summary_var, justify="left").grid(
            row=0, column=1, sticky="w"
        )

        export_frame = ttk.LabelFrame(main_frame, text="Eksport UR CAPS")
        export_frame.grid(row=1, column=0, sticky="ew")
        export_frame.columnconfigure(0, weight=1)

        header_frame = ttk.Frame(export_frame)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.columnconfigure(1, weight=1)

        ttk.Label(header_frame, text="Nazwa:").grid(row=0, column=0, padx=4, pady=2, sticky="e")
        ttk.Entry(header_frame, textvariable=self.pally_name_var, width=28).grid(
            row=0, column=1, padx=4, pady=2, sticky="ew"
        )

        ttk.Label(header_frame, text="Folder:").grid(row=1, column=0, padx=4, pady=2, sticky="e")
        folder_frame = ttk.Frame(header_frame)
        folder_frame.grid(row=1, column=1, padx=4, pady=2, sticky="ew")
        folder_frame.columnconfigure(0, weight=1)
        ttk.Entry(folder_frame, textvariable=self.pally_out_dir_var).grid(
            row=0, column=0, padx=(0, 4), sticky="ew"
        )
        ttk.Button(folder_frame, text="...", width=3, command=self._choose_directory).grid(
            row=0, column=1
        )

        pattern_frame = ttk.Frame(header_frame)
        pattern_frame.grid(row=2, column=0, columnspan=2, padx=4, pady=2, sticky="w")
        ttk.Button(pattern_frame, text="Zapisz wzór", command=self._save_pattern).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(pattern_frame, text="Wczytaj wzór", command=self._load_pattern).pack(
            side=tk.LEFT
        )
        ttk.Button(
            pattern_frame,
            text="Wczytaj PPB / PALLY JSON",
            command=self.import_pally_json,
        ).pack(side=tk.LEFT, padx=(6, 0))

        basic_frame = ttk.LabelFrame(export_frame, text="BASIC")
        basic_frame.grid(row=1, column=0, sticky="ew", padx=4, pady=(4, 6))
        basic_frame.columnconfigure(0, weight=1)

        basic_grid = ttk.Frame(basic_frame)
        basic_grid.grid(row=0, column=0, sticky="ew", padx=4, pady=2)
        basic_grid.columnconfigure(0, weight=0)
        basic_grid.columnconfigure(1, weight=1)

        basic_left = ttk.Frame(basic_grid)
        basic_left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        basic_left.columnconfigure(1, weight=1)

        basic_right = ttk.Frame(basic_grid)
        basic_right.grid(row=0, column=1, sticky="nsew")
        basic_right.columnconfigure(1, weight=1)

        ttk.Label(basic_left, text="Kierunek etykiety:").grid(
            row=0, column=0, padx=4, pady=2, sticky="e"
        )
        ttk.Combobox(
            basic_left,
            textvariable=self.pally_label_orientation_display_var,
            values=list(self.pally_label_orientation_map.keys()),
            state="readonly",
            width=25,
        ).grid(row=0, column=1, padx=4, pady=2, sticky="w")

        ttk.Label(basic_left, text="Swap axes for PALLY (EUR):").grid(
            row=1, column=0, padx=4, pady=2, sticky="e"
        )
        ttk.Checkbutton(
            basic_left,
            variable=self.pally_swap_axes_var,
        ).grid(row=1, column=1, padx=4, pady=2, sticky="w")

        ttk.Label(basic_left, text="Nadpisz wysokość całkowitą (mm):").grid(
            row=2, column=0, padx=4, pady=2, sticky="e"
        )
        ttk.Entry(
            basic_left,
            textvariable=self.dimensions_height_override_var,
            width=18,
        ).grid(row=2, column=1, padx=4, pady=2, sticky="w")

        ttk.Label(basic_left, text="Nadpisz wysokość palety (mm):").grid(
            row=3, column=0, padx=4, pady=2, sticky="e"
        )
        ttk.Entry(
            basic_left,
            textvariable=self.pallet_height_override_var,
            width=18,
        ).grid(row=3, column=1, padx=4, pady=2, sticky="w")

        ttk.Label(basic_right, text="Lewa paleta:").grid(
            row=0, column=0, padx=4, pady=2, sticky="e"
        )
        ttk.Combobox(
            basic_right,
            textvariable=self.left_palette_mode_var,
            values=["mirror", "altPattern"],
            state="readonly",
            width=25,
        ).grid(row=0, column=1, padx=4, pady=2, sticky="w")

        ttk.Checkbutton(
            basic_right,
            text="Auto-mirror PALLY (bez altPattern)",
            variable=self.omit_altpattern_when_mirror_var,
        ).grid(row=1, column=1, padx=4, pady=2, sticky="w")

        approach_help = (
            "Approach (prawa) steruje kierunkiem odkładania dla prawej palety, "
            "altApproach dla lewej.\n"
            "normal – od dalszej strony palety do środka.\n"
            "inverse – od bliższej strony palety na zewnątrz.\n"
            "Strzałki w podglądzie pokazują kierunek podejścia."
        )
        approach_label_frame = ttk.Frame(basic_right)
        approach_label_frame.grid(row=2, column=0, padx=4, pady=2, sticky="e")
        ttk.Label(approach_label_frame, text="Approach (prawa):").pack(side=tk.LEFT)
        ttk.Button(
            approach_label_frame,
            text="?",
            width=3,
            command=lambda: messagebox.showinfo("Approach", approach_help),
        ).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Combobox(
            basic_right,
            textvariable=self.approach_right_var,
            values=["normal", "inverse"],
            state="readonly",
            width=25,
        ).grid(row=2, column=1, padx=4, pady=2, sticky="w")

        ttk.Label(basic_right, text="Approach (lewa):").grid(
            row=3, column=0, padx=4, pady=2, sticky="e"
        )
        ttk.Combobox(
            basic_right,
            textvariable=self.approach_left_var,
            values=["normal", "inverse"],
            state="readonly",
            width=25,
        ).grid(row=3, column=1, padx=4, pady=2, sticky="w")

        slips_frame = ttk.LabelFrame(basic_right, text="Przekładki + masa")
        slips_frame.grid(row=4, column=0, columnspan=2, padx=4, pady=(4, 4), sticky="ew")
        slips_frame.columnconfigure(1, weight=1)

        ttk.Label(slips_frame, text="Przekładki po warstwie:").grid(
            row=0, column=0, columnspan=2, pady=(2, 0), sticky="w"
        )
        self.pally_slip_frame = ttk.Frame(slips_frame)
        self.pally_slip_frame.grid(row=1, column=0, columnspan=2, sticky="w")

        slip_buttons = ttk.Frame(slips_frame)
        slip_buttons.grid(row=2, column=0, columnspan=2, pady=(2, 0), sticky="w")
        ttk.Button(slip_buttons, text="Wszystkie", command=self._slips_select_all).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(slip_buttons, text="Wyczyść", command=self._slips_clear_all).pack(
            side=tk.LEFT
        )

        ttk.Label(slips_frame, textvariable=self.slip_summary_var, justify="left").grid(
            row=3, column=0, columnspan=2, pady=(2, 0), sticky="w"
        )

        ttk.Label(slips_frame, text="Masa kartonu (kg):").grid(
            row=4, column=0, padx=4, pady=(4, 0), sticky="e"
        )
        ttk.Entry(
            slips_frame,
            textvariable=self.box_weight_override_var,
            width=8,
            validate="key",
            validatecommand=(self.register(self._validate_weight_override), "%P"),
        ).grid(row=4, column=1, padx=4, pady=(6, 0), sticky="w")

        ttk.Button(
            export_frame,
            text="Eksportuj PALLY JSON",
            command=self.export_pally_json,
        ).grid(row=2, column=0, padx=4, pady=(6, 2), sticky="ew")

        ttk.Checkbutton(
            export_frame,
            text="Pretty JSON",
            variable=self.pretty_json_var,
        ).grid(row=3, column=0, padx=4, pady=(0, 2), sticky="w")

        ttk.Label(
            export_frame,
            textvariable=self.status_var,
            justify="left",
            wraplength=780,
        ).grid(row=4, column=0, padx=4, pady=(2, 0), sticky="w")

        preview_frame = ttk.LabelFrame(main_frame, text="Podgląd warstwy")
        preview_frame.grid(row=2, column=0, sticky="nsew", pady=(6, 0))
        preview_frame.columnconfigure(0, weight=3)
        preview_frame.columnconfigure(1, weight=2)
        preview_frame.rowconfigure(1, weight=1)

        controls_frame = ttk.Frame(preview_frame)
        controls_frame.grid(row=0, column=0, sticky="ew", padx=4, pady=2)
        controls_frame.columnconfigure(1, weight=1)

        ttk.Label(controls_frame, text="Warstwa:").grid(
            row=0, column=0, padx=4, pady=2, sticky="e"
        )
        self.preview_layer_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.preview_layer_var,
            state="readonly",
            width=10,
        )
        self.preview_layer_combo.grid(row=0, column=1, padx=4, pady=2, sticky="w")
        self.preview_layer_combo.bind("<<ComboboxSelected>>", self._render_layer_preview)

        canvas_frame = ttk.Frame(preview_frame)
        canvas_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 2))
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        self.preview_fig, (self.preview_ax_right, self.preview_ax_left) = plt.subplots(
            1, 2, figsize=(7.2, 3.1)
        )
        self.preview_axes = {"right": self.preview_ax_right, "left": self.preview_ax_left}
        self.preview_canvas = FigureCanvasTkAgg(self.preview_fig, master=canvas_frame)
        self.preview_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        manual_frame = ttk.LabelFrame(preview_frame, text="Tryb ręczny")
        manual_frame.grid(row=1, column=1, sticky="nsew", padx=4, pady=(0, 2))
        manual_frame.columnconfigure(0, weight=1)

        mode_row = ttk.Frame(manual_frame)
        mode_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))
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

        target_row = ttk.Frame(manual_frame)
        target_row.grid(row=1, column=0, sticky="ew", pady=(0, 2))
        ttk.Label(target_row, text="Edytuj kolejność dla:").grid(
            row=0, column=0, padx=(0, 6), sticky="w"
        )
        ttk.Radiobutton(
            target_row,
            text="Prawa",
            value="right",
            variable=self.manual_edit_target_var,
            command=self._render_layer_preview,
        ).grid(row=0, column=1, padx=2, sticky="w")
        ttk.Radiobutton(
            target_row,
            text="Lewa",
            value="left",
            variable=self.manual_edit_target_var,
            command=self._render_layer_preview,
        ).grid(row=0, column=2, padx=2, sticky="w")
        ttk.Radiobutton(
            target_row,
            text="Obie",
            value="both",
            variable=self.manual_edit_target_var,
            command=self._render_layer_preview,
        ).grid(row=0, column=3, padx=2, sticky="w")

        sync_row = ttk.Frame(manual_frame)
        sync_row.grid(row=2, column=0, sticky="ew", pady=(0, 4))
        ttk.Checkbutton(
            sync_row,
            text="Parzyste + nieparzyste razem",
            variable=self.manual_sync_parity_var,
        ).grid(row=0, column=0, sticky="w")

        self.manual_hint_label = ttk.Label(
            manual_frame,
            textvariable=self.manual_hint_var,
            wraplength=220,
            justify="left",
        )
        self.manual_hint_label.grid(row=3, column=0, sticky="w", pady=(0, 4))

        self.order_tree = ttk.Treeview(
            manual_frame,
            columns=("pozycja",),
            show="headings",
            selectmode="browse",
            height=7,
        )
        self.order_tree.heading("pozycja", text="Kolejność")
        self.order_tree.column("pozycja", width=80, anchor="center")
        self.order_tree.grid(row=4, column=0, sticky="nsew")

        controls_row = ttk.Frame(manual_frame)
        controls_row.grid(row=5, column=0, sticky="ew", pady=4)
        self.manual_up_button = ttk.Button(
            controls_row, text="Góra", command=self._move_selected_up
        )
        self.manual_up_button.grid(row=0, column=0, padx=2)
        self.manual_down_button = ttk.Button(
            controls_row, text="Dół", command=self._move_selected_down
        )
        self.manual_down_button.grid(row=0, column=1, padx=2)

        manual_frame.rowconfigure(4, weight=1)

        self.order_tree.bind("<<TreeviewSelect>>", self._update_manual_move_buttons)
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
            loaded = self.pallet_tab.load_pattern_dialog()
            if not loaded:
                self.status_var.set("Anulowano wczytywanie")
                return
            self.fetch_from_pallet(quiet_if_missing=True)
            self.status_var.set("Wczytano wzór i odświeżono dane")
        except Exception:
            logger.exception("Failed to load pattern from UR CAPS")

    def import_pally_json(self) -> None:
        path = filedialog.askopenfilename(
            title="Wczytaj PPB / PALLY JSON",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            self.status_var.set("Anulowano wczytywanie")
            return

        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to load PALLY JSON")
            messagebox.showerror(
                "Błąd wczytywania", f"Nie udało się wczytać pliku: {exc}"
            )
            return

        if not self._validate_pally_payload(payload):
            messagebox.showerror("Nieprawidłowy plik", "Brak wymaganych pól PPB.")
            return

        self.loaded_payload = payload
        self._apply_pally_payload_to_controls(payload)
        layer_count = self._payload_layer_count(payload)
        self._refresh_preview_layers(layer_count)
        self._render_layer_preview()
        self.status_var.set(f"Wczytano PPB: {os.path.basename(path)}")
        self._update_slip_summary()

    @staticmethod
    def _validate_pally_payload(payload: dict) -> bool:
        if not payload:
            return False
        has_version = "PPB_VERSION_NO" in payload or "PPB_VERSION_NO" in payload.get(
            "guiSettings", {}
        )
        if not has_version:
            return False
        for key in ("dimensions", "productDimensions", "layerTypes", "layers"):
            if key not in payload:
                return False
        return True

    @staticmethod
    def _payload_layer_count(payload: dict) -> int:
        layer_types = {lt.get("name"): lt for lt in payload.get("layerTypes", [])}
        count = 0
        for layer_name in payload.get("layers", []):
            layer_type = layer_types.get(layer_name)
            if not layer_type or layer_type.get("class") == "separator":
                continue
            count += 1
        return count

    def _apply_pally_payload_to_controls(self, payload: dict) -> None:
        self.pally_name_var.set(payload.get("name") or "export")
        dimensions = payload.get("dimensions", {})
        height_val = dimensions.get("height")
        pallet_height_val = dimensions.get("palletHeight")
        self.dimensions_height_override_var.set(
            "" if height_val is None else str(height_val)
        )
        self.pallet_height_override_var.set(
            "" if pallet_height_val is None else str(pallet_height_val)
        )
        product_dims = payload.get("productDimensions", {})
        weight_g = product_dims.get("weight")
        if weight_g is not None:
            self.box_weight_override_var.set(f"{float(weight_g) / 1000:.3f}")
        else:
            self.box_weight_override_var.set("")
        gui_settings = payload.get("guiSettings", {})
        self.left_palette_mode_var.set(gui_settings.get("altLayout", "mirror"))

        label_orientation = payload.get("labelOrientation")
        if label_orientation is not None:
            display_map = {
                value: name for name, value in self.pally_label_orientation_map.items()
            }
            self.pally_label_orientation_display_var.set(
                display_map.get(int(label_orientation), self.pally_label_orientation_display_var.get())
            )

        approach_right = "normal"
        approach_left = "normal"
        for layer_type in payload.get("layerTypes", []):
            if layer_type.get("class") == "layer":
                approach_right = layer_type.get("approach", approach_right)
                approach_left = layer_type.get("altApproach", approach_right)
                break
        self.approach_right_var.set(approach_right)
        self.approach_left_var.set(approach_left)

        layer_count = self._payload_layer_count(payload)
        self._update_slip_checkboxes(layer_count)
        layer_types = {lt.get("name"): lt for lt in payload.get("layerTypes", [])}
        layers = payload.get("layers", [])
        base_slip = False
        if layers:
            first_type = layer_types.get(layers[0], {})
            base_slip = first_type.get("class") == "separator"
        if self.pally_slip_vars:
            self.pally_slip_vars[0].set(base_slip)
        product_idx = 0
        for idx, layer_name in enumerate(layers):
            layer_type = layer_types.get(layer_name)
            if not layer_type or layer_type.get("class") == "separator":
                continue
            product_idx += 1
            next_name = layers[idx + 1] if idx + 1 < len(layers) else None
            next_type = layer_types.get(next_name, {})
            slip_after = next_type.get("class") == "separator"
            if product_idx < len(self.pally_slip_vars):
                self.pally_slip_vars[product_idx].set(slip_after)

        self.omit_altpattern_when_mirror_var.set(False)
        self.pretty_json_var.set(True)
        self._update_weight_summary()
        self._update_slip_summary()

    def export_ui_state(self) -> dict:
        return {
            "name": self.pally_name_var.get(),
            "output_dir": self.pally_out_dir_var.get(),
            "label_orientation_display": self.pally_label_orientation_display_var.get(),
            "swap_axes_for_pally": bool(self.pally_swap_axes_var.get()),
            "left_palette_mode": self.left_palette_mode_var.get(),
            "approach_right": self.approach_right_var.get(),
            "approach_left": self.approach_left_var.get(),
            "placement_sequence": self.placement_sequence_var.get(),
            "pallet_height_override": self.pallet_height_override_var.get(),
            "dimensions_height_override": self.dimensions_height_override_var.get(),
            "slips_base": bool(self.pally_slip_vars[0].get()) if self.pally_slip_vars else True,
            "slips_after": sorted(self._selected_slip_layers()),
            "box_weight_override": self.box_weight_override_var.get(),
            "omit_altpattern_when_mirror": bool(self.omit_altpattern_when_mirror_var.get()),
            "pretty_json": bool(self.pretty_json_var.get()),
            "manual_mode": bool(self.manual_mode_var.get()),
            "manual_edit_target": self.manual_edit_target_var.get(),
            "manual_sync_parity": bool(self.manual_sync_parity_var.get()),
            "manual_orders": self.manual_orders,
        }

    def apply_ui_state(self, state: dict) -> None:
        if not state:
            return
        self.pally_name_var.set(state.get("name", self.pally_name_var.get()))
        self.pally_out_dir_var.set(
            state.get("output_dir", self.pally_out_dir_var.get())
        )
        self.pally_label_orientation_display_var.set(
            state.get("label_orientation_display", self.pally_label_orientation_display_var.get())
        )
        self.pally_swap_axes_var.set(
            bool(state.get("swap_axes_for_pally", self.pally_swap_axes_var.get()))
        )
        self.left_palette_mode_var.set(
            state.get("left_palette_mode", self.left_palette_mode_var.get())
        )
        self.approach_right_var.set(
            state.get("approach_right", self.approach_right_var.get())
        )
        self.approach_left_var.set(
            state.get("approach_left", self.approach_left_var.get())
        )
        self.placement_sequence_var.set(
            state.get("placement_sequence", self.placement_sequence_var.get())
        )
        self.pallet_height_override_var.set(state.get("pallet_height_override", ""))
        self.dimensions_height_override_var.set(
            state.get("dimensions_height_override", "")
        )
        self.box_weight_override_var.set(state.get("box_weight_override", ""))
        self.omit_altpattern_when_mirror_var.set(
            bool(state.get("omit_altpattern_when_mirror", False))
        )
        self.pretty_json_var.set(bool(state.get("pretty_json", True)))
        if self.pally_slip_vars:
            self.pally_slip_vars[0].set(bool(state.get("slips_base", True)))
            slips_after = {int(x) for x in state.get("slips_after", []) if isinstance(x, int)}
            for idx, var in enumerate(self.pally_slip_vars):
                if idx == 0:
                    continue
                var.set(idx in slips_after)

        snapshot = self.active_snapshot
        if snapshot is not None:
            try:
                ur_config = self._collect_config()
                preview_config = self._make_pally_config(snapshot, ur_config, name_override="preview")
                self._update_signature_context(snapshot, preview_config)
            except Exception:
                logger.exception("Failed to refresh signature context from UR CAPS state")

        self.manual_mode_var.set(bool(state.get("manual_mode", False)))
        self.manual_edit_target_var.set(
            state.get("manual_edit_target", self.manual_edit_target_var.get())
        )
        self.manual_sync_parity_var.set(
            bool(state.get("manual_sync_parity", False))
        )
        manual_orders = state.get("manual_orders") or {}
        if not manual_orders and state.get("manual_orders_by_side"):
            manual_orders = self._upgrade_manual_orders(
                state.get("manual_orders_by_side") or {}
            )
        if manual_orders:
            if snapshot is not None:
                pruned_orders: dict[str, dict[str, list[int]]] = {}
                dropped = False
                for signature, orders in manual_orders.items():
                    if signature not in self.signature_to_layers:
                        dropped = True
                        continue
                    rect_count = self._signature_rect_count(snapshot, signature)
                    right_order = orders.get("right", [])
                    left_order = orders.get("left", [])
                    if rect_count and len(right_order) == rect_count and len(left_order) == rect_count:
                        pruned_orders[signature] = {
                            "right": list(right_order),
                            "left": list(left_order),
                        }
                    else:
                        dropped = True
                self.manual_orders = pruned_orders
                if dropped:
                    self.status_var.set(
                        "Część zapisanych kolejności ręcznych nie pasuje do aktualnego wzoru."
                    )
            else:
                self.manual_orders = manual_orders

        self._update_weight_summary()
        self._update_slip_summary()
        self._render_layer_preview()

    def fetch_from_pallet(self, quiet_if_missing: bool = False) -> None:
        snapshot = None
        snapshot_builders = [
            getattr(self.pallet_tab, "build_ur_caps_snapshot", None),
            getattr(self.pallet_tab, "get_current_snapshot", None),
        ]

        for builder in snapshot_builders:
            if not callable(builder):
                continue
            try:
                snapshot = builder()
            except Exception:
                logger.exception("Snapshot builder failed in UR CAPS fetch")
                snapshot = None
            if snapshot is not None:
                break
        if snapshot is None:
            message = "Nie udało się pobrać aktualnego układu z Paletyzacji."
            if quiet_if_missing:
                self.status_var.set(message)
                return
            messagebox.showinfo("UR CAPS", message)
            return
        self.apply_snapshot(snapshot)

    def apply_snapshot(self, snapshot: PalletSnapshot) -> None:
        previous_orders = {
            signature: dict(orders) for signature, orders in self.manual_orders.items()
        }

        self.active_snapshot = snapshot
        self.manual_orders = previous_orders
        self.layer_signatures = []
        self.signature_to_layers = {}
        self.loaded_payload = None
        self._update_snapshot_summary(snapshot)
        if snapshot.box_weight_g is not None:
            weight_kg = float(snapshot.box_weight_g) / 1000
            weight_text = f"{weight_kg:.3f}"
        else:
            weight_text = ""
        if self.box_weight_override_var.get() != weight_text:
            self.box_weight_override_var.set(weight_text)
        layer_count = snapshot.num_layers or len(snapshot.layers)
        self._update_slip_checkboxes(layer_count)
        for idx, var in enumerate(self.pally_slip_vars):
            if idx and idx in snapshot.slips_after:
                var.set(True)
        self._update_slip_summary()
        self.pally_swap_axes_var.set(snapshot.pallet_w > snapshot.pallet_l)
        self.status_var.set("Dane z Paletyzacji odświeżone")
        self._update_weight_summary()
        try:
            ur_config = self._collect_config()
            preview_config = self._make_pally_config(
                snapshot, ur_config, name_override="preview"
            )
            self._update_signature_context(snapshot, preview_config)
        except Exception:
            logger.exception("Failed to refresh signature context for snapshot")

        self._prune_manual_orders()
        self._refresh_preview_layers(layer_count)
        self._render_layer_preview()

    def _update_snapshot_summary(self, snapshot: PalletSnapshot) -> None:
        pallet = f"Paleta: {snapshot.pallet_w} × {snapshot.pallet_l} × {snapshot.pallet_h} mm"
        box = f"Karton: {snapshot.box_w} × {snapshot.box_l} × {snapshot.box_h} mm"
        layer_count = snapshot.num_layers or len(snapshot.layers)
        layers = f"Warstwy: {layer_count}"
        self.snapshot_summary_var.set(f"{pallet} | {box} | {layers}")

    def _update_weight_summary(self) -> None:
        weight_g, source = self._get_box_weight_g()
        if source == "invalid_override":
            self.weight_summary_var.set("Masa kartonu: nieprawidłowa")
            return
        if weight_g:
            self.weight_summary_var.set(f"Masa kartonu: {weight_g / 1000:.3f} kg")
        else:
            self.weight_summary_var.set("Masa kartonu: brak danych")

    def _update_slip_checkboxes(self, layer_count: int) -> None:
        for widget in self.pally_slip_frame.winfo_children():
            widget.destroy()
        self.pally_slip_vars.clear()
        base_var = tk.BooleanVar(value=True)
        base_var.trace_add("write", self._update_slip_summary)
        self.pally_slip_vars.append(base_var)
        ttk.Checkbutton(
            self.pally_slip_frame,
            text="0",
            variable=base_var,
        ).grid(row=0, column=0, padx=2, pady=0, sticky="w")

        per_row = 10
        for idx in range(1, layer_count + 1):
            var = tk.BooleanVar(value=False)
            var.trace_add("write", self._update_slip_summary)
            self.pally_slip_vars.append(var)
            disp_idx = idx
            row = disp_idx // per_row
            col = disp_idx % per_row
            ttk.Checkbutton(
                self.pally_slip_frame,
                text=str(idx),
                variable=var,
            ).grid(row=row, column=col, padx=2, pady=0, sticky="w")
        self._update_slip_summary()

    def _selected_slip_layers(self) -> set[int]:
        slips: set[int] = set()
        for idx, var in enumerate(self.pally_slip_vars):
            if idx == 0:
                continue
            if var.get():
                slips.add(idx)
        return slips

    def _update_slip_summary(self, *_: object) -> None:
        if not self.pally_slip_vars:
            self.slip_summary_var.set("Przekładki (eksport): -")
            return
        base = "TAK" if self.pally_slip_vars[0].get() else "NIE"
        layers = sorted(self._selected_slip_layers())
        if layers:
            layers_text = ", ".join(map(str, layers))
        else:
            layers_text = "brak"
        self.slip_summary_var.set(
            f"Przekładki (eksport): baza={base} | warstwy: {layers_text}"
        )

    def _slips_select_all(self) -> None:
        for var in self.pally_slip_vars[1:]:
            var.set(True)

    def _slips_clear_all(self) -> None:
        for var in self.pally_slip_vars[1:]:
            var.set(False)

    @staticmethod
    def _validate_weight_override(value: str) -> bool:
        if value == "":
            return True
        try:
            float_value = float(value.replace(",", "."))
        except ValueError:
            return False
        return float_value >= 0

    @staticmethod
    def _parse_optional_int(value: str) -> int | None:
        value = value.strip()
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    @staticmethod
    def _slugify_filename(value: str) -> str:
        slug = re.sub(r"[^\w\-]+", "_", value.strip().lower())
        slug = slug.strip("_")
        return slug or "export"

    def _bind_preview_traces(self) -> None:
        for var in (
            self.pally_label_orientation_display_var,
            self.pally_swap_axes_var,
            self.left_palette_mode_var,
            self.approach_left_var,
            self.approach_right_var,
            self.omit_altpattern_when_mirror_var,
        ):
            var.trace_add("write", self._render_layer_preview)

    @staticmethod
    def _upgrade_manual_orders(
        manual_orders_by_side: dict[str, dict[str, list[int]]]
    ) -> dict[str, dict[str, list[int]]]:
        upgraded: dict[str, dict[str, list[int]]] = {}
        for side, orders in manual_orders_by_side.items():
            for signature, order in orders.items():
                upgraded.setdefault(signature, {}).setdefault("right", [])
                upgraded.setdefault(signature, {}).setdefault("left", [])
                upgraded[signature][side] = list(order)
        return upgraded

    def _manual_mode_enabled(self) -> bool:
        return bool(self.manual_mode_var.get())

    def _edit_target_sides(self) -> list[str]:
        target = self.manual_edit_target_var.get()
        if target == "left":
            if self.left_palette_mode_var.get() == "mirror":
                return ["right"]
            return ["left"]
        if target == "right":
            return ["right"]
        if self.left_palette_mode_var.get() == "mirror":
            return ["right"]
        return ["right", "left"]

    def _display_side(self) -> str:
        if self.left_palette_mode_var.get() == "mirror":
            return "right"
        return "left" if self.manual_edit_target_var.get() == "left" else "right"

    def _signature_rect_count(self, snapshot: PalletSnapshot, signature: str) -> int:
        for layer_idx in self.signature_to_layers.get(signature, []):
            if 0 < layer_idx <= len(snapshot.layer_rects_list):
                return len(snapshot.layer_rects_list[layer_idx - 1])
        return 0

    def _parity_signature_sets(self) -> tuple[set[str], set[str]]:
        odd_signatures: set[str] = set()
        even_signatures: set[str] = set()
        for idx, signature in enumerate(self.layer_signatures, start=1):
            if idx % 2:
                odd_signatures.add(signature)
            else:
                even_signatures.add(signature)
        return odd_signatures, even_signatures

    def _resolve_parity_sync_signatures(
        self, signature: str, layer_idx: int
    ) -> tuple[str | None, str | None, str | None]:
        odd_signatures, even_signatures = self._parity_signature_sets()
        if layer_idx % 2:
            current_set = odd_signatures
            parity_label = "nieparzystych"
        else:
            current_set = even_signatures
            parity_label = "parzystych"
        if signature not in current_set:
            return None, None, "Nie można sparować warstw parzystych/nieparzystych."
        if len(even_signatures) != 1:
            return (
                None,
                None,
                "Synchronizacja wyłączona: brak jednoznacznego układu warstw parzystych.",
            )
        if len(odd_signatures) != 1:
            return (
                None,
                None,
                f"Synchronizacja wyłączona: różne układy warstw {parity_label}.",
            )
        return next(iter(even_signatures)), next(iter(odd_signatures)), None

    def _validate_parity_sync(
        self, signature: str, layer_idx: int
    ) -> tuple[str | None, str | None]:
        snapshot = self.active_snapshot
        if snapshot is None:
            return None, None
        even_signature, odd_signature, reason = self._resolve_parity_sync_signatures(
            signature, layer_idx
        )
        if even_signature is None or odd_signature is None:
            self.manual_sync_parity_var.set(False)
            if reason:
                self.status_var.set(reason)
            return None, None
        even_count = self._signature_rect_count(snapshot, even_signature)
        odd_count = self._signature_rect_count(snapshot, odd_signature)
        if not even_count or even_count != odd_count:
            self.manual_sync_parity_var.set(False)
            self.status_var.set(
                "Synchronizacja wyłączona: różna liczba kartonów w parach."
            )
            return None, None
        return even_signature, odd_signature

    def _apply_manual_order_update(
        self,
        signature: str,
        orders_by_side: dict[str, list[int]],
        layer_idx: int,
    ) -> None:
        if self.left_palette_mode_var.get() == "mirror":
            order = orders_by_side.get("right") or orders_by_side.get("left")
            if order is None:
                return
            orders_by_side = {"right": order}

        if self.manual_sync_parity_var.get():
            even_signature, odd_signature = self._validate_parity_sync(
                signature, layer_idx
            )
            if even_signature and odd_signature:
                self._store_manual_orders_for_signature(
                    even_signature, orders_by_side
                )
                self._store_manual_orders_for_signature(odd_signature, orders_by_side)
                return

        self._store_manual_orders_for_signature(signature, orders_by_side)

    def _store_manual_order(
        self, signature: str, order: list[int], target_sides: list[str]
    ) -> None:
        entry = self.manual_orders.setdefault(signature, {"right": [], "left": []})
        if self.left_palette_mode_var.get() == "mirror":
            entry["right"] = list(order)
            entry["left"] = list(order)
            return
        for side in target_sides:
            entry[side] = list(order)

    def _store_manual_orders_for_signature(
        self, signature: str, orders_by_side: dict[str, list[int]]
    ) -> None:
        for side, order in orders_by_side.items():
            self._store_manual_order(signature, order, [side])

    def _on_manual_mode_toggle(self) -> None:
        snapshot = self.active_snapshot
        if snapshot and self._manual_mode_enabled():
            layer_idx = self._selected_layer_index(len(snapshot.layer_rects_list))
            signature = self._current_signature(layer_idx)
            if signature:
                rect_count = len(snapshot.layer_rects_list[layer_idx - 1])
                self._ensure_manual_order_for_signature(signature, rect_count, "right")
                self._ensure_manual_order_for_signature(signature, rect_count, "left")
        self._render_layer_preview()

    def _current_signature(self, layer_idx: int) -> str | None:
        if not self.layer_signatures or layer_idx - 1 >= len(self.layer_signatures):
            return None
        return self.layer_signatures[layer_idx - 1]

    def _ensure_manual_order_for_signature(
        self, signature: str, rect_count: int, side: str
    ) -> list[int]:
        entry = self.manual_orders.setdefault(signature, {"right": [], "left": []})
        if self.left_palette_mode_var.get() == "mirror":
            order = entry.get("right")
            if not order or len(order) != rect_count:
                order = list(range(rect_count))
                entry["right"] = order
            entry["left"] = list(order)
            return order
        order = entry.get(side)
        if not order or len(order) != rect_count:
            order = list(range(rect_count))
            entry[side] = order
        return order

    def _manual_orders_payload(
        self, snapshot: PalletSnapshot
    ) -> tuple[dict[str, list[int]], dict[str, list[int]]] | None:
        if not self._manual_mode_enabled():
            return None
        orders_right: dict[str, list[int]] = {}
        orders_left: dict[str, list[int]] = {}
        for idx, rects in enumerate(snapshot.layer_rects_list, start=1):
            signature = self._current_signature(idx)
            if not signature:
                continue
            rect_count = len(rects)
            orders_right[signature] = list(
                self._ensure_manual_order_for_signature(signature, rect_count, "right")
            )
            orders_left[signature] = list(
                self._ensure_manual_order_for_signature(signature, rect_count, "left")
            )
        if self.left_palette_mode_var.get() == "mirror":
            orders_left = {sig: list(order) for sig, order in orders_right.items()}
        return orders_right, orders_left

    def _on_manual_sync_parity_toggle(self, *_: object) -> None:
        if not self.manual_sync_parity_var.get():
            return
        snapshot = self.active_snapshot
        if snapshot is None:
            return
        layer_idx = self._selected_layer_index(len(snapshot.layer_rects_list))
        signature = self._current_signature(layer_idx)
        if not signature:
            self.manual_sync_parity_var.set(False)
            self.status_var.set("Synchronizacja wyłączona: brak układu warstwy.")
            return
        even_signature, odd_signature = self._validate_parity_sync(signature, layer_idx)
        if not even_signature or not odd_signature:
            return
        rect_count = len(snapshot.layer_rects_list[layer_idx - 1])
        target_sides = self._edit_target_sides()
        base_side = self._display_side()
        order = self._ensure_manual_order_for_signature(signature, rect_count, base_side)
        self._store_manual_order(even_signature, order, target_sides)
        self._store_manual_order(odd_signature, order, target_sides)
        self._render_layer_preview()

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

    def _prune_manual_orders(self) -> None:
        valid_signatures = set(self.layer_signatures)
        for signature in list(self.manual_orders.keys()):
            if signature not in valid_signatures:
                self.manual_orders.pop(signature, None)

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

    def _refresh_order_tree(self, order: list[int], selected_index: int | None = None) -> None:
        current_selection = self.order_tree.selection()
        if selected_index is None and current_selection:
            selected_index = self.order_tree.index(current_selection[0])

        for item in self.order_tree.get_children():
            self.order_tree.delete(item)
        for box_idx in order:
            self.order_tree.insert("", "end", values=(box_idx + 1,))
        if selected_index is not None and 0 <= selected_index < len(order):
            item_id = self.order_tree.get_children()[selected_index]
            self.order_tree.selection_set(item_id)
            self.order_tree.see(item_id)

        if self._manual_mode_enabled():
            self.order_tree.state(("!disabled",))
            self.manual_hint_label.state(("!disabled",))
        else:
            self.order_tree.state(("disabled",))
            self.manual_hint_label.state(("disabled",))
        self._update_manual_move_buttons()

    def _update_manual_move_buttons(self, *_: object) -> None:
        if not self._manual_mode_enabled():
            self.manual_up_button.state(("disabled",))
            self.manual_down_button.state(("disabled",))
            return
        items = self.order_tree.get_children()
        selection = self.order_tree.selection()
        if not items or not selection:
            self.manual_up_button.state(("disabled",))
            self.manual_down_button.state(("disabled",))
            return
        selected_index = self.order_tree.index(selection[0])
        if selected_index <= 0:
            self.manual_up_button.state(("disabled",))
        else:
            self.manual_up_button.state(("!disabled",))
        if selected_index >= len(items) - 1:
            self.manual_down_button.state(("disabled",))
        else:
            self.manual_down_button.state(("!disabled",))

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
        target_sides = self._edit_target_sides()
        selection = self.order_tree.selection()
        if not selection:
            return
        selected_index = self.order_tree.index(selection[0])
        base_side = self._display_side()
        base_order = self._ensure_manual_order_for_signature(
            signature,
            len(snapshot.layer_rects_list[layer_idx - 1]),
            base_side,
        )
        rect_count = len(base_order)
        target = selected_index + delta
        if target < 0 or target >= rect_count:
            return
        orders_by_side: dict[str, list[int]] = {}
        for side in target_sides:
            order = self._ensure_manual_order_for_signature(signature, rect_count, side)
            value = order.pop(selected_index)
            order.insert(target, value)
            orders_by_side[side] = order
        self._apply_manual_order_update(signature, orders_by_side, layer_idx)
        self._render_layer_preview(selected_index=target)

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
        rect_count = len(snapshot.layer_rects_list[layer_idx - 1])
        target_sides = self._edit_target_sides()
        orders_by_side = {}
        for side in target_sides:
            order = self._ensure_manual_order_for_signature(signature, rect_count, side)
            order.reverse()
            orders_by_side[side] = order
        self._apply_manual_order_update(signature, orders_by_side, layer_idx)
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
        target_sides = self._edit_target_sides()
        order = list(range(rect_count))
        orders_by_side = {side: list(order) for side in target_sides}
        self._apply_manual_order_update(signature, orders_by_side, layer_idx)
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
            omit_altpattern_when_mirror=bool(
                self.omit_altpattern_when_mirror_var.get()
            ),
            pallet_height_override=self._parse_optional_int(
                self.pallet_height_override_var.get()
            ),
            dimensions_height_override=self._parse_optional_int(
                self.dimensions_height_override_var.get()
            ),
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
            pallet_height_override=ur_config.pallet_height_override,
            dimensions_height_override=ur_config.dimensions_height_override,
            omit_altpattern_when_mirror=ur_config.omit_altpattern_when_mirror,
        )

    def _choose_directory(self) -> None:
        path = filedialog.askdirectory(initialdir=self.pally_out_dir_var.get())
        if path:
            self.pally_out_dir_var.set(path)

    def _get_box_weight_g(self) -> tuple[int, str]:
        override_raw = self.box_weight_override_var.get().strip()
        if override_raw:
            try:
                weight_kg = float(override_raw.replace(",", "."))
            except ValueError:
                return 0, "invalid_override"
            return int(round(weight_kg * 1000)), "ur_caps_override"
        snapshot = self.active_snapshot
        if snapshot is not None and snapshot.box_weight_g is not None:
            return max(int(snapshot.box_weight_g), 0), snapshot.box_weight_source
        if hasattr(self.pallet_tab, "_get_active_carton_weight"):
            weight_kg, source = self.pallet_tab._get_active_carton_weight()  # pylint: disable=protected-access
            return int(round(max(weight_kg, 0.0) * 1000)), source
        return 0, "unknown"

    def _on_weight_override_changed(self, *_: object) -> None:
        raw = self.box_weight_override_var.get().strip()
        if not raw:
            self._update_weight_summary()
            return
        try:
            weight_kg = float(raw.replace(",", "."))
        except ValueError:
            self.status_var.set("Nieprawidłowa masa kartonu w UR CAPS.")
            self._update_weight_summary()
            return
        if weight_kg < 0:
            self.status_var.set("Nieprawidłowa masa kartonu w UR CAPS.")
            self._update_weight_summary()
            return
        if hasattr(self.pallet_tab, "manual_carton_weight_var"):
            manual_var = getattr(self.pallet_tab, "manual_carton_weight_var", None)
            if manual_var is not None and hasattr(manual_var, "set"):
                manual_var.set(f"{weight_kg:.3f}")
                if hasattr(self.pallet_tab, "update_summary"):
                    try:
                        self.pallet_tab.update_summary()
                    except Exception:
                        logger.exception("Failed to update pallet summary after override sync")
                elif hasattr(self.pallet_tab, "_on_manual_weight_changed"):
                    try:
                        self.pallet_tab._on_manual_weight_changed()  # pylint: disable=protected-access
                    except Exception:
                        logger.exception("Failed to update pallet manual weight after override sync")
        if self.active_snapshot is not None:
            self.active_snapshot.box_weight_g = int(round(weight_kg * 1000))
            self.active_snapshot.box_weight_source = "manual"
        self._update_weight_summary()

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
        return build_pally_json(
            config=config,
            layer_rects_list=snapshot.layer_rects_list,
            slips_after=self._selected_slip_layers(),
            include_base_slip=(
                bool(self.pally_slip_vars[0].get()) if self.pally_slip_vars else True
            ),
            manual_orders_by_signature_right=None,
            manual_orders_by_signature_left=None,
        )

    def _extract_layer_patterns(
        self, payload: dict, layer_idx: int
    ) -> tuple[list[dict], list[dict], str, str] | None:
        layer_types = {lt.get("name"): lt for lt in payload.get("layerTypes", [])}
        gui_settings = payload.get("guiSettings", {})
        alt_layout = gui_settings.get("altLayout", "mirror")
        layer_counter = 0
        for layer_name in payload.get("layers", []):
            layer_type = layer_types.get(layer_name)
            if not layer_type or layer_type.get("class") == "separator":
                continue
            layer_counter += 1
            if layer_counter == layer_idx:
                pattern = layer_type.get("pattern") or []
                alt_pattern = layer_type.get("altPattern")
                if alt_pattern is None:
                    if alt_layout == "mirror":
                        pallet_w = float(payload.get("dimensions", {}).get("width", 0) or 0)
                        alt_pattern = mirror_pattern(pattern, pallet_w)
                    else:
                        alt_pattern = list(pattern)
                approach = layer_type.get("approach", "normal")
                alt_approach = layer_type.get("altApproach", approach)
                return pattern, alt_pattern, approach, alt_approach
        return None

    def _force_preview_redraw(self) -> None:
        try:
            self.preview_canvas.draw()
            self.preview_canvas.get_tk_widget().update_idletasks()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to redraw UR CAPS preview")

    def _draw_empty_preview(self, message: str) -> None:
        for side, ax in self.preview_axes.items():
            ax.clear()
            ax.axis("off")
            ax.text(
                0.5,
                0.5,
                message,
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
        self.current_preview_signature = None
        self._clear_preview_overlay()
        self._force_preview_redraw()

    def _clear_preview_overlay(self) -> None:
        for artist in self.preview_overlay_artists:
            try:
                artist.remove()
            except ValueError:
                pass
        self.preview_overlay_artists.clear()

    def _draw_preview_orientation_overlay(self) -> None:
        self._clear_preview_overlay()
        axes = [self.preview_ax_right, self.preview_ax_left]
        positions = sorted([ax.get_position() for ax in axes], key=lambda pos: pos.x0)
        left_pos, right_pos = positions
        gap = max(right_pos.x0 - left_pos.x1, 0.03)
        gap_mid = (left_pos.x1 + right_pos.x0) / 2
        center_y = (left_pos.y0 + left_pos.y1) / 2
        radius = min(0.03, gap * 0.4)

        robot = Circle(
            (gap_mid, center_y),
            radius=radius,
            transform=self.preview_fig.transFigure,
            facecolor="#74b9ff",
            edgecolor="#0984e3",
            lw=2,
            zorder=10,
        )
        self.preview_fig.add_artist(robot)
        self.preview_overlay_artists.append(robot)

        robot_text = self.preview_fig.text(
            gap_mid,
            center_y,
            "ROBOT",
            ha="center",
            va="center",
            fontsize=8,
            fontweight="bold",
            color="#0984e3",
            zorder=11,
        )
        self.preview_overlay_artists.append(robot_text)

        top_y = min(max(left_pos.y1, right_pos.y1) + 0.02, 0.97)
        top_box = Rectangle(
            (gap_mid - 0.05, top_y - 0.012),
            0.10,
            0.024,
            transform=self.preview_fig.transFigure,
            facecolor="#ffeaa7",
            edgecolor="#d35400",
            lw=1.2,
            zorder=9,
        )
        self.preview_fig.add_artist(top_box)
        self.preview_overlay_artists.append(top_box)
        top_text = self.preview_fig.text(
            gap_mid,
            top_y,
            "POBÓR KARTONU",
            ha="center",
            va="center",
            fontsize=7,
            color="#d35400",
            zorder=10,
        )
        self.preview_overlay_artists.append(top_text)

        bottom_y = max(min(left_pos.y0, right_pos.y0) - 0.03, 0.03)
        bottom_box = Rectangle(
            (gap_mid - 0.05, bottom_y - 0.012),
            0.10,
            0.024,
            transform=self.preview_fig.transFigure,
            facecolor="#ffcccc",
            edgecolor="#c0392b",
            lw=1.2,
            zorder=9,
        )
        self.preview_fig.add_artist(bottom_box)
        self.preview_overlay_artists.append(bottom_box)
        bottom_text = self.preview_fig.text(
            gap_mid,
            bottom_y,
            "PRZÓD",
            ha="center",
            va="center",
            fontsize=8,
            fontweight="bold",
            color="#c0392b",
            zorder=10,
        )
        self.preview_overlay_artists.append(bottom_text)

    def _draw_layer_pattern(
        self,
        ax,
        payload: dict,
        pattern: list[dict],
        layer_idx: int,
        approach: str,
        side: str,
        order: list[int] | None = None,
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

        ax.clear()
        side_label = "prawa" if side == "right" else "lewa"
        ax.set_title(f"Warstwa {layer_idx} ({side_label})")
        ax.set_aspect("equal")
        ax.add_patch(Rectangle((0, 0), pallet_w, pallet_l, fill=False, edgecolor="black", lw=1.5))

        centers: list[tuple[float, float]] = []
        centers_by_idx: dict[int, tuple[float, float]] = {}
        order_map = None
        if order:
            order_map = {box_idx: idx + 1 for idx, box_idx in enumerate(order)}
        for idx, item in enumerate(pattern, start=1):
            rotation = (item.get("r") or [0])[0]
            width, length = (
                (product_w, product_l) if rotation in (0, 180) else (product_l, product_w)
            )
            x_center = float(item.get("x", 0))
            y_center = float(item.get("y", 0))
            x_left = x_center - width / 2.0
            y_bottom = y_center - length / 2.0
            box_idx = idx - 1
            ax.add_patch(
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
            ax.text(
                x_center,
                y_center,
                str(order_map.get(box_idx, idx) if order_map else idx),
                ha="center",
                va="center",
                fontsize=9,
                color="#0b5394",
                fontweight="bold",
            )
            ax.text(
                x_center,
                y_center + min(length, width) * 0.18,
                f"{rotation}",
                ha="center",
                va="center",
                fontsize=7,
                color="#0b5394",
            )
            centers.append((x_center, y_center))
            centers_by_idx[box_idx] = (x_center, y_center)

        ordered_centers = centers
        if order:
            ordered_centers = [
                centers_by_idx[box_idx]
                for box_idx in order
                if box_idx in centers_by_idx
            ]
        for prev_center, next_center in zip(ordered_centers, ordered_centers[1:]):
            ax.annotate(
                "",
                xy=next_center,
                xytext=prev_center,
                arrowprops={"arrowstyle": "->", "color": "#cc0000", "lw": 1.2},
            )

        ax.set_xlim(0, max(pallet_w, max((c[0] for c in centers), default=0)))
        ax.set_ylim(0, max(pallet_l, max((c[1] for c in centers), default=0)))
        ax.grid(True, linestyle="--", alpha=0.2)
        ax.set_xlabel("Szerokość [mm]")
        ax.set_ylabel("Długość [mm]")
        self._draw_approach_arrow(ax, pallet_w, pallet_l, approach, side)

    def _draw_approach_arrow(
        self, ax, pallet_w: float, pallet_l: float, approach: str, side: str
    ) -> None:
        arrow_color = "#7f3fbf"
        is_inverse = approach == "inverse"
        if is_inverse:
            start_y, end_y = pallet_l * 0.85, pallet_l * 0.15
        else:
            start_y, end_y = pallet_l * 0.15, pallet_l * 0.85
        margin = pallet_w * 0.08
        x = pallet_w - margin if side == "right" else margin
        ax.annotate(
            "",
            xy=(x, end_y),
            xytext=(x, start_y),
            arrowprops={"arrowstyle": "-|>", "color": arrow_color, "alpha": 0.7, "lw": 2},
        )
        ax.plot([x], [start_y], marker="o", color=arrow_color, markersize=4, alpha=0.9)
        direction_label = "inverse (od tyłu)" if is_inverse else "normal (od frontu)"
        ha = "right" if side == "right" else "left"
        x_offset = -margin * 0.3 if side == "right" else margin * 0.3
        ax.text(
            x + x_offset,
            (start_y + end_y) / 2,
            f"{side.upper()}: {direction_label}",
            ha=ha,
            va="center",
            color="black",
            fontsize=9,
            bbox={"boxstyle": "round,pad=0.2", "fc": "#f3e6ff", "ec": "none", "alpha": 0.7},
        )

    def _render_layer_preview(self, *args, selected_index: int | None = None) -> None:  # noqa: ARG002
        payload: dict | None
        layer_count: int
        signature: str | None = None

        if self.loaded_payload:
            payload = self.loaded_payload
            layer_count = self._payload_layer_count(payload)
            self.manual_mode_var.set(False)
        else:
            snapshot = self.active_snapshot
            if snapshot is None or not snapshot.layer_rects_list:
                self._draw_empty_preview("Brak danych do podglądu")
                return
            layer_count = len(snapshot.layer_rects_list)
            payload = self._build_preview_payload(snapshot)
            signature = self._current_signature(
                self._selected_layer_index(layer_count)
            )

        if not payload:
            self._draw_empty_preview("Brak danych do podglądu")
            return

        layer_idx = self._selected_layer_index(max(layer_count, 1))
        self._refresh_preview_layers(layer_count)

        patterns = self._extract_layer_patterns(payload, layer_idx)
        if not patterns:
            self._draw_empty_preview("Brak wzoru warstwy")
            return
        pattern, alt_pattern, approach_right, approach_left = patterns

        self.current_preview_signature = signature
        self._update_manual_hint(signature, layer_idx)

        if signature and self._manual_mode_enabled():
            if self.manual_sync_parity_var.get():
                even_signature, odd_signature = self._validate_parity_sync(
                    signature, layer_idx
                )
                if even_signature and odd_signature:
                    for side in ("right", "left"):
                        side_order = self._ensure_manual_order_for_signature(
                            signature,
                            len(pattern) if side == "right" else len(alt_pattern),
                            side,
                        )
                        self._store_manual_order(even_signature, side_order, [side])
                        self._store_manual_order(odd_signature, side_order, [side])
            order_right = self._ensure_manual_order_for_signature(
                signature, len(pattern), "right"
            )
            order_left = self._ensure_manual_order_for_signature(
                signature, len(alt_pattern), "left"
            )
        else:
            order_right = list(range(len(pattern)))
            order_left = list(range(len(alt_pattern)))

        display_order = order_left if self._display_side() == "left" else order_right
        self._refresh_order_tree(display_order, selected_index=selected_index)

        try:
            self._draw_layer_pattern(
                self.preview_ax_right,
                payload,
                pattern,
                layer_idx,
                approach_right,
                "right",
                order_right if signature and self._manual_mode_enabled() else None,
            )
            self._draw_layer_pattern(
                self.preview_ax_left,
                payload,
                alt_pattern,
                layer_idx,
                approach_left,
                "left",
                order_left if signature and self._manual_mode_enabled() else None,
            )
            self._draw_preview_orientation_overlay()
            self._force_preview_redraw()
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

        box_weight_g, source = self._get_box_weight_g()
        if source == "invalid_override":
            messagebox.showwarning(
                "UR CAPS",
                "Nieprawidłowa masa kartonu w polu override.",
            )
            return
        if not box_weight_g:
            messagebox.showwarning(
                "Brak masy",
                "Brak masy kartonu — uzupełnij w Paletyzacji lub wpisz override w UR CAPS.",
            )
            return

        layer_rects_list = snapshot.layer_rects_list
        if not layer_rects_list:
            messagebox.showwarning("UR CAPS", "Brak współrzędnych warstw w snapshot.")
            return

        config = self._make_pally_config(snapshot, ur_config)
        self._update_signature_context(snapshot, config)
        manual_orders = self._manual_orders_payload(snapshot)
        orders_right, orders_left = manual_orders if manual_orders else (None, None)

        payload = build_pally_json(
            config=config,
            layer_rects_list=layer_rects_list,
            slips_after=ur_config.slips_after,
            include_base_slip=bool(self.pally_slip_vars[0].get()) if self.pally_slip_vars else True,
            manual_orders_by_signature_right=orders_right,
            manual_orders_by_signature_left=orders_left,
        )

        warnings = find_out_of_bounds(payload)
        if warnings:
            self.status_var.set(f"Błąd: {warnings[0]}")
            return

        os.makedirs(ur_config.output_dir, exist_ok=True)
        filename = f"{self._slugify_filename(ur_config.name)}.json"
        path = os.path.join(ur_config.output_dir, filename)
        with open(path, "w", encoding="utf-8") as handle:
            if self.pretty_json_var.get():
                json.dump(payload, handle, indent=4, ensure_ascii=False)
            else:
                json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        self._update_slip_summary()
        self._update_weight_summary()
        self.status_var.set(
            f"Zapisano PALLY JSON: {path} | {self.slip_summary_var.get()} | "
            f"{self.weight_summary_var.get()}"
        )

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
    omit_altpattern_when_mirror: bool = False
    pallet_height_override: int | None = None
    dimensions_height_override: int | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["slips_after"] = sorted(self.slips_after)
        return data
