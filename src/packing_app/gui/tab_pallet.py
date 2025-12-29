import json
import logging
import math
import os
import queue
import re
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from typing import List, Tuple, Dict, Optional

import matplotlib

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from palletizer_core.pattern_format import (
    apply_pattern_data as apply_pattern_data_core,
    gather_pattern_data as gather_pattern_data_core,
)
from palletizer_core.pattern_io import (
    ensure_pattern_dir,
    get_pattern_dir,
    save_pattern,
)
from palletizer_core.pally_export import (
    PallyExportConfig,
    build_pally_json,
    find_out_of_bounds,
    parse_slips_after,
)
from palletizer_core.transformations import (
    apply_transformation as apply_transformation_core,
    inverse_transformation as inverse_transformation_core,
)
from packing_app.gui.editor_controller import EditorController
from packing_app.gui.pallet_state_apply import apply_layout_result_to_tab_state
from palletizer_core import Carton, Pallet
from palletizer_core.engine import (
    LayerLayout,
    LayoutComputation,
    PalletInputs,
    build_layouts,
    group_cartons,
)
from palletizer_core.selector import (
    RISK_CONTACT_THRESHOLD,
    RISK_STABILITY_THRESHOLD,
    RISK_SUPPORT_THRESHOLD,
)
from palletizer_core.solutions import Solution, SolutionCatalog, display_for_key
from palletizer_core.units import parse_float
from palletizer_core.stacking import compute_max_stack, compute_num_layers
from palletizer_core.validation import validate_pallet_inputs
from packing_app.data.repository import (
    load_cartons,
    load_pallets,
    load_cartons_with_weights,
    load_pallets_with_weights,
    load_materials,
    load_slip_sheets,
)


logger = logging.getLogger(__name__)


def apply_pattern_selection_after_restore(tab, previous_flag: bool, target_key: str) -> bool:
    setattr(tab, "_suspend_pattern_apply", previous_flag)
    if not target_key:
        return False
    tree = getattr(tab, "pattern_tree", None)
    if tree is None:
        return False
    selection = tree.selection()
    if selection and selection[0] == target_key:
        tab.on_pattern_select()
        return True
    return False


def filter_selection_for_layer(selected_indices, layer_idx: int):
    return {(layer, idx) for layer, idx in selected_indices if layer == layer_idx}


def parse_dim(var: tk.StringVar) -> float:
    try:
        val = parse_float(var.get())
        return max(0, val)
    except Exception:
        messagebox.showwarning("Błąd", "Wprowadzono niepoprawną wartość. Użyto 0.")
        return 0.0


class TabPallet(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.predefined_cartons = load_cartons()
        self.predefined_pallets = load_pallets()
        self.carton_weights = {k: v[3] for k, v in load_cartons_with_weights().items()}
        self.pallet_weights = {
            p["name"]: p["weight"] for p in load_pallets_with_weights()
        }
        self.material_weights = load_materials()
        slips = load_slip_sheets()
        self.slip_sheet_weight = slips[0] if slips else 0
        first_carton = list(self.predefined_cartons.keys())[0]
        initial_weight = self.carton_weights.get(first_carton, 0)
        self.manual_carton_weight_var = tk.StringVar(
            value=self._format_number(initial_weight) if initial_weight else ""
        )
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        self.pally_name_var = tk.StringVar(value="export")
        self.pally_out_dir_var = tk.StringVar(
            value=os.path.join(base_dir, "pally_exports")
        )
        self.pally_slips_after_var = tk.StringVar(value="")
        self.pally_overhang_ends_var = tk.StringVar(value="0")
        self.pally_overhang_sides_var = tk.StringVar(value="0")
        self.pally_label_orientation_var = tk.IntVar(value=180)
        self.pally_swap_axes_var = tk.BooleanVar(value=False)
        self.pally_result_path_var = tk.StringVar(value="Plik wynikowy: -")
        self.pallet_base_mass = 25.0
        self.pack(fill=tk.BOTH, expand=True)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.layouts = []
        self.layers = []
        self.carton_ids = []
        self.layer_patterns = []
        self.transformations = []
        self.products_per_carton_var = tk.StringVar(value="1")
        self._updating_products_per_carton = False
        self._last_2d_products_per_carton = ""
        self.tape_per_carton = 0.0
        self.film_per_pallet = 0.0
        self.best_layout_name = ""
        self.best_layout_key = ""
        self.best_even = []
        self.best_odd = []
        self.solution_catalog: SolutionCatalog = SolutionCatalog.empty()
        self.solution_by_key: Dict[str, Solution] = {}
        self.modify_mode_var = tk.BooleanVar(value=False)
        self.show_numbers_var = tk.BooleanVar(value=True)
        self.patches = []
        self.selected_indices = set()
        self.editor_controller = EditorController()
        self.drag_offset = (0, 0)
        self.drag_info = None
        self.drag_button = None
        self.drag_select_origin = None
        self._layer_sync_source = "height"
        self._suspend_layer_sync = False
        self._suspend_pattern_apply = False
        self._apply_after_id = None
        self._pending_key = None
        self._pending_force = False
        self._current_applied_key = None
        self._apply_in_progress = False
        self._compute_queue: queue.Queue = queue.Queue()
        self._compute_job_id = 0
        self._compute_polling = False
        self._redraw_pending = False
        self._redraw_timer = None
        self._debug_call_counts = {
            "update_summary": 0,
            "update_pattern_stats": 0,
            "on_pattern_select": 0,
        }
        self.drag_snapshot_saved = False
        self.press_cid = None
        self.motion_cid = None
        self.release_cid = None
        self.key_cid = None
        self.context_menu = None
        self.context_layer = 0
        self.context_pos = (0, 0)
        self.undo_stack = []
        self.row_by_row_vertical_var = tk.IntVar(value=0)
        self.row_by_row_horizontal_var = tk.IntVar(value=0)
        self._row_by_row_user_modified = False
        self._updating_row_by_row = False
        self.build_ui()

    @staticmethod
    def _option_width(options, padding: int = 2) -> int:
        """Return the width of an OptionMenu sized to its content."""
        return max((len(str(opt)) for opt in options), default=0) + padding

    def layers_linked(self) -> bool:
        """Return True if odd and even layers use the same layout algorithm."""
        try:
            odd_key = self._solution_key_from_display(self.odd_layout_var.get())
            even_key = self._solution_key_from_display(self.even_layout_var.get())
            return bool(odd_key and even_key and odd_key == even_key)
        except Exception:
            return False

    def build_ui(self):
        main_paned = ttk.Panedwindow(self, orient=tk.VERTICAL)
        main_paned.grid(row=0, column=0, sticky="nsew", padx=12, pady=10)

        content_panel = ttk.Frame(main_paned)
        content_panel.columnconfigure(0, weight=1)
        content_panel.columnconfigure(1, weight=1)
        for i in range(4):
            content_panel.rowconfigure(i, weight=1 if i == 0 else 0)
        main_paned.add(content_panel, weight=4)

        self.pattern_stats_frame = ttk.LabelFrame(
            content_panel, text="Ocena stabilności"
        )
        self.pattern_stats_frame.grid(
            row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=(0, 10)
        )
        self.pattern_stats_frame.columnconfigure(0, weight=1)
        self.pattern_stats_frame.rowconfigure(0, weight=1)
        self.pattern_stats_frame.rowconfigure(1, weight=0)

        self.summary_frame = ttk.LabelFrame(content_panel, text="Podsumowanie")
        self.summary_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 10))
        for i in range(6):
            self.summary_frame.rowconfigure(i, weight=0)
        self.summary_frame.columnconfigure(1, weight=1)

        carton_frame = ttk.LabelFrame(content_panel, text="Parametry kartonu")
        carton_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=(0, 10))
        for col in range(0, 4):
            carton_frame.columnconfigure(col, weight=1)

        layers_frame = ttk.LabelFrame(content_panel, text="Ustawienia warstw")
        layers_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=(0, 10))
        for col in range(6):
            layers_frame.columnconfigure(col, weight=1)

        actions_frame = ttk.LabelFrame(content_panel, text="Akcje i status")
        actions_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=(0, 5))
        actions_frame.columnconfigure(0, weight=1)

        self.pallet_var = tk.StringVar(value=self.predefined_pallets[0]["name"])
        pallet_options = [p["name"] for p in self.predefined_pallets]
        self.pallet_w_var = tk.StringVar(value=str(self.predefined_pallets[0]["w"]))
        self.pallet_l_var = tk.StringVar(value=str(self.predefined_pallets[0]["l"]))
        self.pallet_h_var = tk.StringVar(value=str(self.predefined_pallets[0]["h"]))
        self.pally_swap_axes_var.set(
            float(self.pallet_w_var.get()) > float(self.pallet_l_var.get())
        )
        self.pallet_dims_var = tk.StringVar(value="")

        ttk.Label(layers_frame, text="Paleta:").grid(
            row=0, column=0, padx=5, pady=6, sticky="w"
        )
        pallet_menu = ttk.OptionMenu(
            layers_frame,
            self.pallet_var,
            self.predefined_pallets[0]["name"],
            *pallet_options,
            command=self.on_pallet_selected,
        )
        pallet_menu.config(width=self._option_width(pallet_options))
        pallet_menu.grid(row=0, column=1, padx=5, pady=6, sticky="w")

        ttk.Label(layers_frame, text="W/L/H [mm]:").grid(
            row=0, column=2, padx=5, pady=6, sticky="w"
        )
        ttk.Label(layers_frame, textvariable=self.pallet_dims_var).grid(
            row=0, column=3, padx=5, pady=6, sticky="w"
        )
        self.pallet_w_var.trace_add("write", self._update_pallet_dimensions_label)
        self.pallet_l_var.trace_add("write", self._update_pallet_dimensions_label)
        self.pallet_h_var.trace_add("write", self._update_pallet_dimensions_label)
        self._update_pallet_dimensions_label()

        ttk.Label(carton_frame, text="Karton:").grid(
            row=0, column=0, padx=5, pady=4, sticky="w"
        )
        self.carton_var = tk.StringVar(value=list(self.predefined_cartons.keys())[0])
        carton_options = list(self.predefined_cartons.keys())
        carton_menu = ttk.OptionMenu(
            carton_frame,
            self.carton_var,
            list(self.predefined_cartons.keys())[0],
            *carton_options,
            command=self.on_carton_selected,
        )
        carton_menu.config(width=self._option_width(carton_options))
        carton_menu.grid(row=0, column=1, padx=5, pady=4, sticky="w", columnspan=3)

        self.box_w_var = tk.StringVar(
            value=str(
                self.predefined_cartons[list(self.predefined_cartons.keys())[0]][0]
            )
        )
        self.box_l_var = tk.StringVar(
            value=str(
                self.predefined_cartons[list(self.predefined_cartons.keys())[0]][1]
            )
        )
        self.box_h_var = tk.StringVar(
            value=str(
                self.predefined_cartons[list(self.predefined_cartons.keys())[0]][2]
            )
        )

        ttk.Label(carton_frame, text="W (mm):").grid(
            row=1, column=0, padx=5, pady=4, sticky="w"
        )
        entry_box_w = ttk.Entry(carton_frame, textvariable=self.box_w_var, width=8)
        entry_box_w.grid(row=1, column=1, padx=5, pady=4, sticky="w")
        entry_box_w.bind("<Return>", self.compute_pallet)

        ttk.Label(carton_frame, text="L (mm):").grid(
            row=1, column=2, padx=5, pady=4, sticky="w"
        )
        entry_box_l = ttk.Entry(carton_frame, textvariable=self.box_l_var, width=8)
        entry_box_l.grid(row=1, column=3, padx=5, pady=4, sticky="w")
        entry_box_l.bind("<Return>", self.compute_pallet)

        ttk.Label(carton_frame, text="H (mm):").grid(
            row=2, column=0, padx=5, pady=4, sticky="w"
        )
        entry_box_h = ttk.Entry(carton_frame, textvariable=self.box_h_var, width=8)
        entry_box_h.grid(row=2, column=1, padx=5, pady=4, sticky="w")
        entry_box_h.bind("<Return>", self.compute_pallet)

        ttk.Label(carton_frame, text="Grubość tektury (mm):").grid(
            row=2, column=2, padx=5, pady=4, sticky="w"
        )
        self.cardboard_thickness_var = tk.StringVar(value="3")
        entry_cardboard = ttk.Entry(
            carton_frame,
            textvariable=self.cardboard_thickness_var,
            width=8,
            validate="key",
            validatecommand=(self.register(self.validate_number), "%P"),
        )
        entry_cardboard.grid(row=2, column=3, padx=5, pady=4, sticky="w")
        entry_cardboard.bind("<Return>", self.compute_pallet)

        ttk.Label(carton_frame, text="Wymiary zewnętrzne (mm):").grid(
            row=3, column=0, padx=5, pady=4, sticky="w"
        )
        self.ext_dims_label = ttk.Label(carton_frame, text="")
        self.ext_dims_label.grid(
            row=3, column=1, columnspan=3, padx=5, pady=4, sticky="w"
        )
        self.cardboard_thickness_var.trace_add("write", self.update_external_dimensions)
        self.box_w_var.trace_add("write", self.update_external_dimensions)
        self.box_l_var.trace_add("write", self.update_external_dimensions)
        self.box_h_var.trace_add("write", self.update_external_dimensions)
        self.update_external_dimensions()

        ttk.Label(carton_frame, text="Odstęp między kartonami (mm):").grid(
            row=4, column=0, padx=5, pady=4, sticky="w"
        )
        self.spacing_var = tk.StringVar(value="0")
        spacing_frame = ttk.Frame(carton_frame)
        entry_spacing = ttk.Entry(
            spacing_frame,
            textvariable=self.spacing_var,
            width=6,
            validate="key",
            validatecommand=(self.register(self.validate_number), "%P"),
        )
        entry_spacing.pack(side=tk.LEFT)
        ttk.Button(
            spacing_frame, text="+", width=2, command=lambda: self.adjust_spacing(1)
        ).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(
            spacing_frame, text="-", width=2, command=lambda: self.adjust_spacing(-1)
        ).pack(side=tk.LEFT, padx=(4, 0))
        spacing_frame.grid(row=4, column=1, padx=5, pady=4, sticky="w")
        entry_spacing.bind("<Return>", self.compute_pallet)

        ttk.Label(carton_frame, text="Masa kartonu (kg):").grid(
            row=4, column=2, padx=5, pady=4, sticky="w"
        )
        weight_frame = ttk.Frame(carton_frame)
        ttk.Entry(
            weight_frame,
            textvariable=self.manual_carton_weight_var,
            width=8,
            validate="key",
            validatecommand=(self.register(self.validate_number), "%P"),
        ).pack(side=tk.LEFT)
        ttk.Label(weight_frame, text="(pozostaw puste = baza)").pack(
            side=tk.LEFT, padx=5
        )
        weight_frame.grid(row=4, column=3, padx=5, pady=4, sticky="w")

        ttk.Label(layers_frame, text="Liczba warstw:").grid(
            row=1, column=0, padx=5, pady=4, sticky="w"
        )
        self.num_layers_var = tk.StringVar(value="1")
        self.num_layers_var.trace_add("write", self._on_num_layers_changed)
        entry_num_layers = ttk.Entry(
            layers_frame, textvariable=self.num_layers_var, width=5
        )
        entry_num_layers.grid(row=1, column=1, padx=5, pady=4, sticky="w")
        entry_num_layers.bind("<Return>", self.compute_pallet)

        ttk.Label(layers_frame, text="Maksymalna wysokość (mm):").grid(
            row=1, column=2, padx=5, pady=4, sticky="w"
        )
        self.max_stack_var = tk.StringVar(value="1600")
        self.max_stack_var.trace_add("write", self._on_max_stack_changed)
        entry_max_stack = ttk.Entry(
            layers_frame, textvariable=self.max_stack_var, width=8
        )
        entry_max_stack.grid(row=1, column=3, padx=5, pady=4, sticky="w")
        entry_max_stack.bind("<Return>", self.compute_pallet)
        self.include_pallet_height_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            layers_frame,
            text="Uwzględnij wysokość nośnika",
            variable=self.include_pallet_height_var,
            command=self.compute_pallet,
        ).grid(row=1, column=4, columnspan=2, padx=5, pady=4, sticky="w")

        ttk.Label(layers_frame, text="Centrowanie:").grid(
            row=2, column=0, padx=5, pady=4, sticky="w"
        )
        self.center_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            layers_frame, variable=self.center_var, command=self.compute_pallet
        ).grid(row=2, column=1, padx=5, pady=4, sticky="w")

        ttk.Label(layers_frame, text="Tryb:").grid(row=2, column=2, padx=5, pady=4, sticky="w")
        self.center_mode_var = tk.StringVar(value="Cała warstwa")
        center_mode_options = ["Cała warstwa", "Poszczególne obszary"]
        center_mode_menu = ttk.OptionMenu(
            layers_frame,
            self.center_mode_var,
            "Cała warstwa",
            *center_mode_options,
            command=self.compute_pallet,
        )
        center_mode_menu.config(width=self._option_width(center_mode_options))
        center_mode_menu.grid(row=2, column=3, padx=5, pady=4, sticky="w")

        self.shift_even_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            layers_frame,
            text="Przesuwaj warstwy parzyste",
            variable=self.shift_even_var,
            command=self.compute_pallet,
        ).grid(row=2, column=4, padx=5, pady=4, sticky="w")

        self.maximize_mixed = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            layers_frame,
            text="Maksymalizuj mixed",
            variable=self.maximize_mixed,
            command=self.compute_pallet,
        ).grid(row=2, column=5, padx=5, pady=4, sticky="w")

        self.extended_library_var = tk.BooleanVar(value=False)
        self.dynamic_variants_var = tk.BooleanVar(value=False)
        self.deep_search_var = tk.BooleanVar(value=False)
        self.filter_sanity_var = tk.BooleanVar(value=True)
        self.allow_offsets_var = tk.BooleanVar(value=False)
        self.min_support_var = tk.StringVar(value="0.80")
        self.assume_full_support_var = tk.BooleanVar(value=False)
        self.result_limit_var = tk.StringVar(value="30")
        self.generated_patterns_var = tk.StringVar(value="Patterns: raw=0, shown=0")

        advanced_frame = ttk.LabelFrame(layers_frame, text="Zaawansowane")
        advanced_frame.grid(
            row=5, column=0, columnspan=6, padx=5, pady=6, sticky="we"
        )
        advanced_frame.columnconfigure(6, weight=1)
        ttk.Checkbutton(
            advanced_frame,
            text="Extended library patterns",
            variable=self.extended_library_var,
            command=self.compute_pallet,
        ).grid(row=0, column=0, padx=5, pady=4, sticky="w")
        ttk.Checkbutton(
            advanced_frame,
            text="Dynamic variants",
            variable=self.dynamic_variants_var,
            command=self.compute_pallet,
        ).grid(row=0, column=1, padx=5, pady=4, sticky="w")
        ttk.Checkbutton(
            advanced_frame,
            text="Filter nonsense layouts",
            variable=self.filter_sanity_var,
            command=self.compute_pallet,
        ).grid(row=0, column=2, padx=5, pady=4, sticky="w")
        ttk.Checkbutton(
            advanced_frame,
            text="Deep search",
            variable=self.deep_search_var,
            command=self.compute_pallet,
        ).grid(row=0, column=3, padx=5, pady=4, sticky="w")
        ttk.Checkbutton(
            advanced_frame,
            text="Allow offsets (brick) with support check",
            variable=self.allow_offsets_var,
            command=self.compute_pallet,
        ).grid(row=1, column=0, padx=5, pady=4, sticky="w")
        ttk.Label(advanced_frame, text="Min support fraction:").grid(
            row=1, column=1, padx=5, pady=4, sticky="e"
        )
        min_support_entry = ttk.Entry(
            advanced_frame,
            textvariable=self.min_support_var,
            width=6,
            validate="key",
            validatecommand=(self.register(self.validate_number), "%P"),
        )
        min_support_entry.grid(row=1, column=2, padx=5, pady=4, sticky="w")
        min_support_entry.bind("<Return>", self.compute_pallet)
        min_support_entry.bind("<FocusOut>", self.compute_pallet)
        ttk.Label(advanced_frame, text="(0.0–1.0)").grid(
            row=1, column=3, padx=4, pady=4, sticky="w"
        )
        ttk.Label(advanced_frame, text="Result limit:").grid(
            row=1, column=4, padx=5, pady=4, sticky="e"
        )
        result_limit_entry = ttk.Entry(
            advanced_frame,
            textvariable=self.result_limit_var,
            width=6,
            validate="key",
            validatecommand=(self.register(self.validate_number), "%P"),
        )
        result_limit_entry.grid(row=1, column=5, padx=5, pady=4, sticky="w")
        result_limit_entry.bind("<Return>", self.compute_pallet)
        result_limit_entry.bind("<FocusOut>", self.compute_pallet)
        ttk.Checkbutton(
            advanced_frame,
            text="Assume full support with tie-sheet",
            variable=self.assume_full_support_var,
            command=self.compute_pallet,
        ).grid(row=2, column=0, padx=5, pady=4, sticky="w")
        ttk.Label(advanced_frame, textvariable=self.generated_patterns_var).grid(
            row=2, column=1, padx=5, pady=4, sticky="w"
        )

        pally_frame = ttk.LabelFrame(advanced_frame, text="PALLY / UR export")
        pally_frame.grid(
            row=0, column=6, rowspan=3, padx=(10, 5), pady=4, sticky="nsew"
        )
        pally_frame.columnconfigure(0, weight=0)
        pally_frame.columnconfigure(1, weight=1)
        ttk.Label(pally_frame, text="Nazwa:").grid(
            row=0, column=0, padx=5, pady=2, sticky="w"
        )
        ttk.Entry(pally_frame, textvariable=self.pally_name_var, width=22).grid(
            row=0, column=1, padx=5, pady=2, sticky="ew"
        )
        ttk.Label(pally_frame, text="Folder:").grid(
            row=1, column=0, padx=5, pady=2, sticky="w"
        )
        folder_frame = ttk.Frame(pally_frame)
        folder_frame.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        folder_frame.columnconfigure(0, weight=1)
        ttk.Entry(folder_frame, textvariable=self.pally_out_dir_var).grid(
            row=0, column=0, padx=(0, 4), pady=0, sticky="ew"
        )
        ttk.Button(
            folder_frame, text="...", width=3, command=self._choose_pally_directory
        ).grid(row=0, column=1, padx=(0, 0), pady=0)
        ttk.Label(pally_frame, text="Przekładki (warstwy):").grid(
            row=2, column=0, padx=5, pady=2, sticky="w"
        )
        ttk.Entry(
            pally_frame,
            textvariable=self.pally_slips_after_var,
            width=22,
        ).grid(row=2, column=1, padx=5, pady=2, sticky="ew")
        ttk.Label(pally_frame, text="1-based, przecinki; 0 zawsze na drewnie").grid(
            row=3, column=0, columnspan=2, padx=5, pady=(0, 4), sticky="w"
        )

        ttk.Label(pally_frame, text="Overhang końce [mm]:").grid(
            row=4, column=0, padx=5, pady=2, sticky="w"
        )
        ttk.Spinbox(
            pally_frame,
            from_=0,
            to=999,
            textvariable=self.pally_overhang_ends_var,
            width=8,
        ).grid(row=4, column=1, padx=5, pady=2, sticky="w")
        ttk.Label(pally_frame, text="Overhang boki [mm]:").grid(
            row=5, column=0, padx=5, pady=2, sticky="w"
        )
        ttk.Spinbox(
            pally_frame,
            from_=0,
            to=999,
            textvariable=self.pally_overhang_sides_var,
            width=8,
        ).grid(row=5, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(pally_frame, text="Label orientation:").grid(
            row=6, column=0, padx=5, pady=2, sticky="w"
        )
        label_options = [0, -90, 90, 180]
        ttk.OptionMenu(
            pally_frame,
            self.pally_label_orientation_var,
            self.pally_label_orientation_var.get(),
            *label_options,
        ).grid(row=6, column=1, padx=5, pady=2, sticky="w")

        ttk.Checkbutton(
            pally_frame,
            text="Swap axes for PALLY (EUR)",
            variable=self.pally_swap_axes_var,
        ).grid(row=7, column=0, columnspan=2, padx=5, pady=2, sticky="w")

        ttk.Button(
            pally_frame,
            text="Eksportuj PALLY JSON",
            command=self.export_pally_json,
        ).grid(row=8, column=0, columnspan=2, padx=5, pady=4, sticky="ew")
        ttk.Label(
            pally_frame, textvariable=self.pally_result_path_var, wraplength=240
        ).grid(row=9, column=0, columnspan=2, padx=5, pady=(0, 4), sticky="w")

        ttk.Label(layers_frame, text="Liczba przekładek:").grid(
            row=3, column=0, padx=5, pady=4, sticky="w"
        )
        self.slip_count_var = tk.StringVar(value="0")
        entry_slip_count = ttk.Entry(
            layers_frame,
            textvariable=self.slip_count_var,
            width=6,
            validate="key",
            validatecommand=(self.register(self.validate_number), "%P"),
        )
        entry_slip_count.grid(row=3, column=1, padx=5, pady=4, sticky="w")
        entry_slip_count.bind("<Return>", self.compute_pallet)

        ttk.Label(layers_frame, text="Produkty/karton zbiorczy:").grid(
            row=3, column=2, padx=5, pady=4, sticky="w"
        )
        products_frame = ttk.Frame(layers_frame)
        products_frame.grid(row=3, column=3, padx=5, pady=4, sticky="w")
        products_entry = ttk.Entry(
            products_frame,
            textvariable=self.products_per_carton_var,
            width=6,
            validate="key",
            validatecommand=(self.register(self.validate_number), "%P"),
        )
        products_entry.pack(side=tk.LEFT)
        products_entry.bind("<Return>", lambda *_: self._on_products_per_carton_changed())
        products_entry.bind("<FocusOut>", lambda *_: self._on_products_per_carton_changed())
        ttk.Button(
            products_frame,
            text="Pobierz z 2D",
            command=self.use_2d_products_per_carton,
        ).pack(side=tk.LEFT, padx=(6, 0))

        ttk.Label(layers_frame, text="Row by row – linie pionowe:").grid(
            row=3, column=4, padx=5, pady=4, sticky="e"
        )
        vertical_spin = ttk.Spinbox(
            layers_frame,
            from_=0,
            to=999,
            width=5,
            textvariable=self.row_by_row_vertical_var,
            command=lambda: self._on_row_by_row_change("vertical"),
        )
        vertical_spin.grid(row=3, column=5, padx=5, pady=4, sticky="w")
        vertical_spin.bind("<Return>", lambda *_: self._on_row_by_row_change("vertical"))
        vertical_spin.bind("<FocusOut>", lambda *_: self._on_row_by_row_change("vertical"))

        ttk.Label(layers_frame, text="Row by row – linie poziome:").grid(
            row=4, column=0, padx=5, pady=4, sticky="e"
        )
        horizontal_spin = ttk.Spinbox(
            layers_frame,
            from_=0,
            to=999,
            width=5,
            textvariable=self.row_by_row_horizontal_var,
            command=lambda: self._on_row_by_row_change("horizontal"),
        )
        horizontal_spin.grid(row=4, column=1, padx=5, pady=4, sticky="w")
        horizontal_spin.bind(
            "<Return>", lambda *_: self._on_row_by_row_change("horizontal")
        )
        horizontal_spin.bind(
            "<FocusOut>", lambda *_: self._on_row_by_row_change("horizontal")
        )

        self.transform_frame = ttk.Frame(layers_frame)
        self.transform_frame.grid(
            row=1, column=6, rowspan=4, padx=8, pady=4, sticky="ne"
        )

        control_frame = ttk.Frame(actions_frame)
        control_frame.grid(row=0, column=0, sticky="w", padx=5, pady=(4, 0))

        self.compute_btn = ttk.Button(
            control_frame, text="Oblicz", command=self.compute_pallet
        )
        self.compute_btn.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Checkbutton(
            control_frame,
            text="Tryb edycji",
            variable=self.modify_mode_var,
            command=self.toggle_edit_mode,
        ).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(
            control_frame,
            text="Pokaż numerację",
            variable=self.show_numbers_var,
            command=self.draw_pallet,
        ).pack(side=tk.LEFT, padx=6)
        ttk.Button(
            control_frame,
            text="Wstaw karton",
            command=self.insert_carton_button,
        ).pack(side=tk.LEFT, padx=6)
        ttk.Button(
            control_frame,
            text="Usuń karton",
            command=self.delete_selected_carton,
        ).pack(side=tk.LEFT, padx=6)
        ttk.Button(
            control_frame,
            text="Zapisz wzór",
            command=self.save_pattern_dialog,
        ).pack(side=tk.LEFT, padx=6)
        ttk.Button(
            control_frame,
            text="Wczytaj wzór",
            command=self.load_pattern_dialog,
        ).pack(side=tk.LEFT, padx=6)
        self.status_var = tk.StringVar(value="")
        status_frame = ttk.Frame(actions_frame)
        status_frame.columnconfigure(0, weight=1)
        status_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(2, 6))
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, anchor="w")
        self.status_label.grid(row=0, column=0, sticky="w")

        ttk.Label(self.summary_frame, text="Kartonów na palecie:").grid(
            row=0, column=0, padx=6, pady=(6, 2), sticky="w"
        )
        self.totals_label = ttk.Label(
            self.summary_frame, text="", justify="left", font=("TkDefaultFont", 10, "bold")
        )
        self.totals_label.grid(row=0, column=1, padx=6, pady=(6, 2), sticky="w")

        ttk.Label(self.summary_frame, text="Materiały/taśma:").grid(
            row=1, column=0, padx=6, pady=2, sticky="w"
        )
        self.materials_label = ttk.Label(
            self.summary_frame, text="", justify="left"
        )
        self.materials_label.grid(row=1, column=1, padx=6, pady=2, sticky="w")

        ttk.Label(self.summary_frame, text="Masy i ograniczenia:").grid(
            row=2, column=0, padx=6, pady=2, sticky="w"
        )
        self.mass_label = ttk.Label(
            self.summary_frame, text="", justify="left"
        )
        self.mass_label.grid(row=2, column=1, padx=6, pady=2, sticky="w")
        self.limit_label = ttk.Label(
            self.summary_frame, text="", justify="left", foreground="red"
        )
        self.limit_label.grid(row=3, column=1, padx=6, pady=2, sticky="w")

        ttk.Label(self.summary_frame, text="Powierzchnie:").grid(
            row=4, column=0, padx=6, pady=2, sticky="w"
        )
        self.area_label = ttk.Label(
            self.summary_frame, text="", justify="left"
        )
        self.area_label.grid(row=4, column=1, padx=6, pady=2, sticky="w")

        ttk.Label(self.summary_frame, text="Luz przy krawędzi:").grid(
            row=5, column=0, padx=6, pady=(2, 6), sticky="w"
        )
        self.clearance_label = ttk.Label(
            self.summary_frame, text="", justify="left"
        )
        self.clearance_label.grid(row=5, column=1, padx=6, pady=(2, 6), sticky="w")

        columns = (
            "pattern",
            "cartons",
            "stability",
            "layer",
            "cube",
            "support",
            "min_support",
            "contact",
            "clearance",
            "grip",
            "risk",
        )
        self.pattern_tree = ttk.Treeview(
            self.pattern_stats_frame,
            columns=columns,
            show="headings",
            height=16,
        )
        headings = {
            "pattern": "Wzór",
            "cartons": "Kartony",
            "layer": "Warstwa [%]",
            "cube": "Kubatura [%]",
            "stability": "Stabilność [%]",
            "support": "Podparcie [%]",
            "min_support": "Min. podparcie [%]",
            "contact": "Kontakt [%]",
            "clearance": "Min. luz [mm]",
            "grip": "Zmiany chwytu",
            "risk": "Ryzyko",
        }
        for col in columns:
            anchor = "w" if col == "pattern" else "e"
            width = 180 if col == "pattern" else 110
            min_width = 140 if col == "pattern" else 90
            self.pattern_tree.heading(col, text=headings[col])
            self.pattern_tree.column(
                col, anchor=anchor, stretch=True, width=width, minwidth=min_width
            )

        scroll = ttk.Scrollbar(
            self.pattern_stats_frame, orient="vertical", command=self.pattern_tree.yview
        )
        xscroll = ttk.Scrollbar(
            self.pattern_stats_frame, orient="horizontal", command=self.pattern_tree.xview
        )
        self.pattern_tree.configure(
            yscrollcommand=scroll.set, xscrollcommand=xscroll.set, selectmode="browse"
        )
        self.pattern_tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, columnspan=2, sticky="ew")

        self.pattern_detail_var = tk.StringVar(value="")

        self.pattern_tree.bind("<<TreeviewSelect>>", self.on_pattern_select)
        self.pattern_tree.bind(
            "<ButtonRelease-1>", self.on_pattern_click_apply, add="+"
        )

        chart_panel = ttk.Frame(main_paned)
        chart_panel.columnconfigure(0, weight=1)
        chart_panel.rowconfigure(0, weight=1)

        self.fig = plt.Figure(figsize=(9, 3.8))
        self.ax_odd = self.fig.add_subplot(131)
        self.ax_even = self.fig.add_subplot(132)
        self.ax_overlay = self.fig.add_subplot(133)
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_panel)
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.grid(row=0, column=0, sticky="nsew", pady=(8, 0))
        self.canvas.draw()
        main_paned.add(chart_panel, weight=3)

        self.compute_pallet()
        self.manual_carton_weight_var.trace_add("write", self._on_manual_weight_changed)

    def validate_number(self, value):
        if value == "":
            return True
        try:
            float_value = float(value.replace(",", "."))
            return float_value >= 0
        except ValueError:
            return False

    def update_external_dimensions(self, *args):
        try:
            thickness = float(self.cardboard_thickness_var.get().replace(",", "."))
            box_w = float(self.box_w_var.get().replace(",", "."))
            box_l = float(self.box_l_var.get().replace(",", "."))
            box_h = float(self.box_h_var.get().replace(",", "."))
            ext_w = box_w + 2 * thickness
            ext_l = box_l + 2 * thickness
            ext_h = box_h + 2 * thickness
            self.ext_dims_label.config(text=f"{ext_w:.1f} x {ext_l:.1f} x {ext_h:.1f}")
        except ValueError:
            self.ext_dims_label.config(text="Błąd danych")

    @staticmethod
    def _format_number(value) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)):
            try:
                if float(value).is_integer():
                    return str(int(round(float(value))))
            except (TypeError, ValueError):
                return str(value)
            return f"{float(value):.2f}".rstrip("0").rstrip(".")
        return str(value)

    def _debug_log_call(self, name: str) -> None:
        if not logger.isEnabledFor(logging.DEBUG):
            return
        count = self._debug_call_counts.get(name, 0) + 1
        self._debug_call_counts[name] = count
        logger.debug("TabPallet.%s called %d times", name, count)

    def _sync_selection_from_controller(self) -> None:
        self.selected_indices = self.editor_controller.selected_pairs()

    def _set_selection_pairs(self, selection_pairs) -> None:
        self.editor_controller.set_selection_from_pairs(set(selection_pairs))
        self.selected_indices = set(selection_pairs)

    def _clear_selection(self) -> None:
        self.editor_controller.clear_all()
        self.selected_indices.clear()

    def _selection_for_active_layer(self) -> set[tuple[int, int]]:
        active_layer = self.editor_controller.active_layer
        if active_layer is None:
            return set()
        return {
            (active_layer, idx)
            for idx in self.editor_controller.selection_for_layer(active_layer)
        }

    def _update_pallet_dimensions_label(self, *_):
        values = []
        for var in (self.pallet_w_var, self.pallet_l_var, self.pallet_h_var):
            raw = var.get().strip() if hasattr(var, "get") else str(var)
            values.append(self._format_number(raw) if raw else "-")
        self.pallet_dims_var.set(" × ".join(values))

    def _update_pally_swap_axes_default(self) -> None:
        try:
            pallet_w = parse_float(self.pallet_w_var.get())
            pallet_l = parse_float(self.pallet_l_var.get())
        except Exception:
            return
        self.pally_swap_axes_var.set(pallet_w > pallet_l)

    def _get_active_carton_weight(self) -> Tuple[float, str]:
        var = getattr(self, "manual_carton_weight_var", None)
        raw = ""
        if var is not None and hasattr(var, "get"):
            raw = var.get().strip()
        elif isinstance(var, str):
            raw = var.strip()
        if raw:
            try:
                weight = float(raw.replace(",", "."))
            except ValueError:
                return 0.0, "invalid"
            return max(weight, 0.0), "manual"
        weights = getattr(self, "carton_weights", {})
        carton_key = None
        if hasattr(self, "carton_var") and hasattr(self.carton_var, "get"):
            carton_key = self.carton_var.get()
        base_weight = weights.get(carton_key, 0) if carton_key else 0
        return max(base_weight, 0.0), "catalog"

    def _on_manual_weight_changed(self, *_):
        self.update_summary()

    def _set_layer_field(self, var: tk.StringVar, value) -> None:
        formatted = self._format_number(value)
        if var.get() == formatted:
            return
        self._suspend_layer_sync = True
        try:
            var.set(formatted)
        finally:
            self._suspend_layer_sync = False

    def _on_num_layers_changed(self, *_):
        if not self._suspend_layer_sync:
            self._layer_sync_source = "layers"

    def _on_max_stack_changed(self, *_):
        if not self._suspend_layer_sync:
            self._layer_sync_source = "height"

    def _set_row_by_row_counts(self, vertical: int, horizontal: int) -> None:
        if not hasattr(self, "row_by_row_vertical_var"):
            return
        self._updating_row_by_row = True
        try:
            self.row_by_row_vertical_var.set(max(int(vertical), 0))
            self.row_by_row_horizontal_var.set(max(int(horizontal), 0))
        finally:
            self._updating_row_by_row = False

    def _count_row_by_row_rows(
        self, carton: Carton, pattern: LayerLayout | None
    ) -> Tuple[int, int]:
        if not pattern:
            return 0, 0

        vertical_rows: List[float] = []
        horizontal_rows: List[float] = []
        tol = 1e-6
        width = carton.width
        length = carton.length

        for _, y, w, h in pattern:
            if math.isclose(w, width, rel_tol=1e-6, abs_tol=1e-6) and math.isclose(
                h, length, rel_tol=1e-6, abs_tol=1e-6
            ):
                target = vertical_rows
            elif math.isclose(w, length, rel_tol=1e-6, abs_tol=1e-6) and math.isclose(
                h, width, rel_tol=1e-6, abs_tol=1e-6
            ):
                target = horizontal_rows
            else:
                target = vertical_rows if w >= h else horizontal_rows

            if not any(math.isclose(y, existing, rel_tol=1e-6, abs_tol=tol) for existing in target):
                target.append(y)

        return len(vertical_rows), len(horizontal_rows)

    def _build_row_by_row_pattern(
        self, carton: Carton, pallet: Pallet, vertical: int, horizontal: int
    ) -> LayerLayout:
        pattern: LayerLayout = []
        vertical_remaining = max(vertical, 0)
        horizontal_remaining = max(horizontal, 0)
        y = 0.0
        tol = 1e-6
        orientation = "vertical" if vertical_remaining > 0 else "horizontal"

        while y + tol < pallet.length and (
            vertical_remaining > 0 or horizontal_remaining > 0
        ):
            if orientation == "vertical":
                if vertical_remaining <= 0:
                    orientation = "horizontal"
                    continue
                row_height = carton.length
                col_width = carton.width
                if (
                    row_height <= 0
                    or col_width <= 0
                    or y + row_height - tol > pallet.length
                ):
                    break
                n_cols = int(pallet.width // col_width) if col_width > 0 else 0
                if n_cols == 0:
                    vertical_remaining = 0
                    orientation = "horizontal"
                    continue
                for c in range(n_cols):
                    pattern.append((c * col_width, y, col_width, row_height))
                y += row_height
                vertical_remaining -= 1
            else:
                if horizontal_remaining <= 0:
                    orientation = "vertical"
                    continue
                row_height = carton.width
                col_width = carton.length
                if (
                    row_height <= 0
                    or col_width <= 0
                    or y + row_height - tol > pallet.length
                ):
                    break
                n_cols = int(pallet.width // col_width) if col_width > 0 else 0
                if n_cols == 0:
                    horizontal_remaining = 0
                    orientation = "vertical"
                    continue
                for c in range(n_cols):
                    pattern.append((c * col_width, y, col_width, row_height))
                y += row_height
                horizontal_remaining -= 1

            if vertical_remaining <= 0 and horizontal_remaining <= 0:
                break
            if orientation == "vertical":
                orientation = "horizontal" if horizontal_remaining > 0 else "vertical"
            else:
                orientation = "vertical" if vertical_remaining > 0 else "horizontal"

        return pattern

    def _normalize_row_by_row_counts(
        self,
        carton: Carton,
        pallet: Pallet,
        vertical: int,
        horizontal: int,
        axis_changed: str | None = None,
    ) -> Tuple[int, int]:
        vertical = max(int(vertical), 0)
        horizontal = max(int(horizontal), 0)

        row_height_vertical = carton.length
        row_height_horizontal = carton.width
        available_height = pallet.length

        max_vertical_total = (
            int(available_height // row_height_vertical)
            if row_height_vertical > 0
            else 0
        )
        max_horizontal_total = (
            int(available_height // row_height_horizontal)
            if row_height_horizontal > 0
            else 0
        )

        vertical_cols = int(pallet.width // carton.width) if carton.width > 0 else 0
        horizontal_cols = int(pallet.width // carton.length) if carton.length > 0 else 0

        if vertical_cols == 0:
            vertical = 0
        else:
            vertical = min(vertical, max_vertical_total)
        if horizontal_cols == 0:
            horizontal = 0
        else:
            horizontal = min(horizontal, max_horizontal_total)

        if axis_changed == "vertical":
            remaining = available_height - vertical * row_height_vertical
            remaining = max(remaining, 0)
            max_horizontal = (
                int(remaining // row_height_horizontal)
                if row_height_horizontal > 0
                else 0
            )
            horizontal = min(horizontal, max_horizontal)
        elif axis_changed == "horizontal":
            remaining = available_height - horizontal * row_height_horizontal
            remaining = max(remaining, 0)
            max_vertical = (
                int(remaining // row_height_vertical)
                if row_height_vertical > 0
                else 0
            )
            vertical = min(vertical, max_vertical)
        else:
            while (
                vertical * row_height_vertical
                + horizontal * row_height_horizontal
                > available_height
                and (vertical > 0 or horizontal > 0)
            ):
                if vertical * row_height_vertical >= horizontal * row_height_horizontal:
                    if vertical > 0:
                        vertical -= 1
                    elif horizontal > 0:
                        horizontal -= 1
                elif horizontal > 0:
                    horizontal -= 1
                else:
                    break

        return max(vertical, 0), max(horizontal, 0)

    def _customize_row_by_row_pattern(
        self,
        carton: Carton,
        pallet: Pallet,
        pattern: LayerLayout | None,
    ) -> Tuple[LayerLayout | None, int, int]:
        custom_pattern, used_vertical, used_horizontal = self._compute_row_by_row_pattern(
            carton,
            pallet,
            pattern,
            self._row_by_row_user_modified,
            self.row_by_row_vertical_var.get(),
            self.row_by_row_horizontal_var.get(),
        )
        self._set_row_by_row_counts(used_vertical, used_horizontal)
        return custom_pattern, used_vertical, used_horizontal

    def _compute_row_by_row_pattern(
        self,
        carton: Carton,
        pallet: Pallet,
        pattern: LayerLayout | None,
        user_modified: bool,
        requested_vertical: int,
        requested_horizontal: int,
    ) -> Tuple[LayerLayout | None, int, int]:
        if not pattern:
            return pattern, 0, 0

        base_vertical, base_horizontal = self._count_row_by_row_rows(carton, pattern)
        if not user_modified:
            requested_vertical = base_vertical
            requested_horizontal = base_horizontal

        normalized_vertical, normalized_horizontal = self._normalize_row_by_row_counts(
            carton,
            pallet,
            requested_vertical,
            requested_horizontal,
        )

        custom_pattern = self._build_row_by_row_pattern(
            carton, pallet, normalized_vertical, normalized_horizontal
        )
        used_vertical, used_horizontal = self._count_row_by_row_rows(
            carton, custom_pattern
        )
        return custom_pattern, used_vertical, used_horizontal

    def _prepare_row_by_row_inputs(self) -> Optional[Tuple[Carton, Pallet]]:
        pallet_w = parse_dim(self.pallet_w_var)
        pallet_l = parse_dim(self.pallet_l_var)
        pallet_h = parse_dim(self.pallet_h_var)
        box_w = parse_dim(self.box_w_var)
        box_l = parse_dim(self.box_l_var)
        box_h = parse_dim(self.box_h_var)
        thickness = parse_dim(self.cardboard_thickness_var)
        spacing = parse_dim(self.spacing_var)

        width = box_w + 2 * thickness + spacing
        length = box_l + 2 * thickness + spacing
        if min(width, length, pallet_w, pallet_l) <= 0:
            return None

        carton = Carton(width, length, box_h)
        pallet = Pallet(pallet_w, pallet_l, pallet_h)
        return carton, pallet

    def _safe_int(self, value) -> int:
        try:
            if isinstance(value, tk.Variable):
                raw = value.get()
            else:
                raw = value
        except tk.TclError:
            return 0

        if isinstance(raw, str):
            raw = raw.strip()
            if not raw:
                return 0
            try:
                raw = float(raw.replace(",", "."))
            except ValueError:
                return 0

        try:
            numeric = float(raw)
        except (TypeError, ValueError):
            return 0

        return max(int(numeric), 0)

    def _on_row_by_row_change(self, axis: str) -> None:
        if self._updating_row_by_row:
            return

        prepared = self._prepare_row_by_row_inputs()
        if not prepared:
            self._set_row_by_row_counts(0, 0)
            return

        carton, pallet = prepared
        current_vertical = self._safe_int(self.row_by_row_vertical_var)
        current_horizontal = self._safe_int(self.row_by_row_horizontal_var)

        normalized_vertical, normalized_horizontal = self._normalize_row_by_row_counts(
            carton,
            pallet,
            current_vertical,
            current_horizontal,
            axis_changed=axis,
        )

        self._row_by_row_user_modified = True
        self._set_row_by_row_counts(normalized_vertical, normalized_horizontal)

        # Always recompute so the preview refreshes immediately after manual
        # edits or pressing Enter inside the spinboxes.
        self.compute_pallet()

    def _get_products_per_carton(self) -> int:
        return self._safe_int(self.products_per_carton_var)

    def _on_products_per_carton_changed(self) -> None:
        value = self._safe_int(self.products_per_carton_var)
        self._updating_products_per_carton = True
        try:
            self.products_per_carton_var.set(str(value))
        finally:
            self._updating_products_per_carton = False
        self.update_summary()

    def set_products_per_carton(self, value, *, from_2d: bool = False) -> None:
        sanitized = self._safe_int(value)
        self._updating_products_per_carton = True
        try:
            self.products_per_carton_var.set(str(sanitized))
        finally:
            self._updating_products_per_carton = False
        if from_2d:
            self._last_2d_products_per_carton = str(sanitized)
        self.update_summary()

    def use_2d_products_per_carton(self) -> None:
        if not self._last_2d_products_per_carton:
            messagebox.showinfo(
                "Brak danych",
                "Brak zapisanych danych z zakładki Pakowanie 2D.",
            )
            return
        self.set_products_per_carton(self._last_2d_products_per_carton)

    def _solution_key_from_display(self, display: str) -> str | None:
        if not display:
            return None
        catalog = getattr(self, "solution_catalog", None)
        if not catalog:
            return None
        display_map = catalog.key_by_display()
        return display_map.get(display)

    def update_transform_frame(self):
        for widget in self.transform_frame.winfo_children():
            widget.destroy()
        layout_options = self.solution_catalog.displays()
        transform_options = [
            "Brak",
            "Odbicie wzdłuż dłuższego boku",
            "Odbicie wzdłuż krótszego boku",
            "Obrót 180°",
        ]

        if not layout_options:
            return

        layout_width = max((len(opt) for opt in layout_options), default=0) + 2
        transform_width = max((len(opt) for opt in transform_options), default=0) + 2

        prev_odd_layout = getattr(self, "odd_layout_var", None)
        prev_even_layout = getattr(self, "even_layout_var", None)
        prev_odd_transform = getattr(self, "odd_transform_var", None)
        prev_even_transform = getattr(self, "even_transform_var", None)

        preferred_row = display_for_key("row_by_row")
        interlock_name = display_for_key("interlock")
        best_layout = getattr(self, "best_layout_name", "")
        if best_layout in layout_options:
            odd_default = best_layout
            even_default = best_layout
        elif preferred_row in layout_options:
            odd_default = preferred_row
            even_default = preferred_row
        elif interlock_name in layout_options:
            odd_default = interlock_name
            even_default = interlock_name
        else:
            odd_default = layout_options[0]
            even_default = odd_default
        if prev_odd_layout and prev_odd_layout.get() in layout_options:
            odd_default = prev_odd_layout.get()
        if prev_even_layout and prev_even_layout.get() in layout_options:
            even_default = prev_even_layout.get()
        odd_tr_default = (
            prev_odd_transform.get() if prev_odd_transform else transform_options[0]
        )
        if prev_even_transform:
            even_tr_default = prev_even_transform.get()
        else:
            pallet_w = parse_dim(self.pallet_w_var)
            pallet_l = parse_dim(self.pallet_l_var)
            even_tr_default = (
                "Odbicie wzdłuż dłuższego boku"
                if pallet_w >= pallet_l
                else "Odbicie wzdłuż krótszego boku"
            )

        ttk.Label(self.transform_frame, text="Warstwy nieparzyste:").grid(
            row=0, column=0, padx=5, pady=2
        )
        self.odd_layout_var = tk.StringVar(value=odd_default)
        odd_menu = ttk.OptionMenu(
            self.transform_frame,
            self.odd_layout_var,
            odd_default,
            *layout_options,
            command=lambda *_: self.update_layers("odd"),
        )
        odd_menu.config(width=layout_width)
        odd_menu.grid(row=0, column=1, padx=5, pady=2)
        self.odd_transform_var = tk.StringVar(value=odd_tr_default)
        odd_transform_menu = ttk.OptionMenu(
            self.transform_frame,
            self.odd_transform_var,
            odd_tr_default,
            *transform_options,
            command=lambda *_: self.update_layers("odd"),
        )
        odd_transform_menu.config(width=transform_width)
        odd_transform_menu.grid(row=0, column=2, padx=5, pady=2)

        ttk.Label(self.transform_frame, text="Warstwy parzyste:").grid(
            row=1, column=0, padx=5, pady=2
        )
        self.even_layout_var = tk.StringVar(value=even_default)
        even_menu = ttk.OptionMenu(
            self.transform_frame,
            self.even_layout_var,
            even_default,
            *layout_options,
            command=lambda *_: self.update_layers("even"),
        )
        even_menu.config(width=layout_width)
        even_menu.grid(row=1, column=1, padx=5, pady=2)
        self.even_transform_var = tk.StringVar(value=even_tr_default)
        even_transform_menu = ttk.OptionMenu(
            self.transform_frame,
            self.even_transform_var,
            even_tr_default,
            *transform_options,
            command=lambda *_: self.update_layers("even"),
        )
        even_transform_menu.config(width=transform_width)
        even_transform_menu.grid(row=1, column=2, padx=5, pady=2)

    def update_layers(self, side="both", force=False, draw: bool = True, draw_idle: bool = False, *args):
        num_layers = getattr(self, "num_layers", int(parse_dim(self.num_layers_var)))
        if side == "both" or not self.layers:
            self.layers = [list() for _ in range(num_layers)]
            self.carton_ids = [list() for _ in range(num_layers)]
            self.layer_patterns = ["" for _ in range(num_layers)]
            self.transformations = ["" for _ in range(num_layers)]
        self._clear_selection()
        self.editor_controller.active_layer = 0
        self.drag_info = None
        if hasattr(self, "undo_stack"):
            self.undo_stack.clear()
        odd_display = self.odd_layout_var.get()
        even_display = self.even_layout_var.get()
        odd_key = self._solution_key_from_display(odd_display) or self.best_layout_key
        even_key = self._solution_key_from_display(even_display) or self.best_layout_key
        odd_solution = self.solution_by_key.get(odd_key) if odd_key else None
        even_solution = self.solution_by_key.get(even_key) if even_key else None
        if not odd_solution and self.solution_catalog.solutions:
            odd_solution = self.solution_catalog.solutions[0]
            odd_key = odd_solution.key
        if not even_solution and self.solution_catalog.solutions:
            even_solution = self.solution_catalog.solutions[0]
            even_key = even_solution.key
        if not odd_solution or not even_solution:
            return
        odd_source = self.best_odd if odd_key == self.best_layout_key else odd_solution.layout
        even_source = self.best_even if even_key == self.best_layout_key else even_solution.layout
        for i in range(1, num_layers + 1):
            idx = i - 1
            if i % 2 == 1:
                if side in ("both", "odd"):
                    if idx >= len(self.layers):
                        self.layers.append(list(odd_source))
                        self.carton_ids.append(list(range(1, len(odd_source) + 1)))
                    elif self.layer_patterns[idx] != odd_key or force:
                        self.layers[idx] = list(odd_source)
                        self.carton_ids[idx] = list(range(1, len(odd_source) + 1))
                    self.layer_patterns[idx] = odd_key
                    self.transformations[idx] = self.odd_transform_var.get()
            else:
                if side in ("both", "even"):
                    if idx >= len(self.layers):
                        self.layers.append(list(even_source))
                        self.carton_ids.append(list(range(1, len(even_source) + 1)))
                    elif self.layer_patterns[idx] != even_key or force:
                        self.layers[idx] = list(even_source)
                        self.carton_ids[idx] = list(range(1, len(even_source) + 1))
                    self.layer_patterns[idx] = even_key
                    self.transformations[idx] = self.even_transform_var.get()
        self.renumber_layers()
        if draw:
            self.draw_pallet(draw_idle=draw_idle)

    def on_pallet_selected(self, *args):
        selected_pallet = next(
            p for p in self.predefined_pallets if p["name"] == self.pallet_var.get()
        )
        self.pallet_w_var.set(str(selected_pallet["w"]))
        self.pallet_l_var.set(str(selected_pallet["l"]))
        self.pallet_h_var.set(str(selected_pallet["h"]))
        self._update_pally_swap_axes_default()
        self.compute_pallet()

    def on_carton_selected(self, *args):
        dims = self.predefined_cartons[self.carton_var.get()]
        self.box_w_var.set(str(dims[0]))
        self.box_l_var.set(str(dims[1]))
        self.box_h_var.set(str(dims[2]))
        weight = self.carton_weights.get(self.carton_var.get(), 0)
        if weight:
            self.manual_carton_weight_var.set(self._format_number(weight))
        else:
            self.manual_carton_weight_var.set("")
        self.compute_pallet()

    @staticmethod
    def apply_transformation(positions, transform, pallet_w, pallet_l):
        return apply_transformation_core(positions, transform, pallet_w, pallet_l)

    @staticmethod
    def inverse_transformation(positions, transform, pallet_w, pallet_l):
        """Reverse the transformation applied to the positions."""
        return inverse_transformation_core(positions, transform, pallet_w, pallet_l)

    def detect_collisions(self, positions, pallet_w, pallet_l):
        """Return indices of cartons that overlap or lie outside the pallet."""

        index_map = {id(pos): idx for idx, pos in enumerate(positions)}
        collisions = set()

        for group in group_cartons(positions):
            if len(group) > 1:
                for pos in group:
                    collisions.add(index_map[id(pos)])

        for idx, (x, y, w, h) in enumerate(positions):
            if x < 0 or y < 0 or x + w > pallet_w or y + h > pallet_l:
                collisions.add(idx)

        return collisions

    def snap_position(self, x, y, w, h, pallet_w, pallet_l, boxes, tol=10):
        """Snap coordinates to pallet edges or nearby cartons."""

        if abs(x) <= tol:
            x = 0
        if abs(y) <= tol:
            y = 0
        if abs(pallet_w - (x + w)) <= tol:
            x = pallet_w - w
        if abs(pallet_l - (y + h)) <= tol:
            y = pallet_l - h

        for bx, by, bw, bh in boxes:
            if abs(x - (bx + bw)) <= tol:
                x = bx + bw
            if abs((x + w) - bx) <= tol:
                x = bx - w
            if abs(y - (by + bh)) <= tol:
                y = by + bh
            if abs((y + h) - by) <= tol:
                y = by - h

        x = min(max(x, 0), pallet_w - w)
        y = min(max(y, 0), pallet_l - h)
        return x, y

    def compute_pallet(self, event=None):
        """Calculate carton layouts on the pallet.

        The row-by-row pattern is selected as the default layout whenever it is
        available. Other patterns are still generated for manual selection.
        """
        self._clear_selection()
        self.drag_info = None
        self._set_compute_status("Obliczanie...", disable_button=True, disable_tree=True)

        inputs = self._read_inputs()
        if not self._validate_inputs(inputs):
            self._set_compute_status("", disable_button=False, disable_tree=False)
            return

        options = self._read_compute_options()
        row_by_row_user_modified = options.pop("row_by_row_user_modified")
        row_by_row_vertical = options.pop("row_by_row_vertical")
        row_by_row_horizontal = options.pop("row_by_row_horizontal")
        job_id = self._next_compute_job_id()

        def row_by_row_customizer(carton: Carton, pallet: Pallet, pattern: LayerLayout | None):
            return self._compute_row_by_row_pattern(
                carton,
                pallet,
                pattern,
                row_by_row_user_modified,
                row_by_row_vertical,
                row_by_row_horizontal,
            )

        thread = threading.Thread(
            target=self._run_compute_job,
            args=(job_id, inputs, options, row_by_row_customizer),
            daemon=True,
        )
        thread.start()
        self._poll_compute_results()

    def _set_compute_status(
        self, text: str, disable_button: bool, *, disable_tree: bool = False
    ) -> None:
        if hasattr(self, "status_var"):
            self.status_var.set(text)
            self.status_label.update_idletasks()
        if hasattr(self, "compute_btn"):
            if disable_button:
                self.compute_btn.state(["disabled"])
            else:
                self.compute_btn.state(["!disabled"])
        if hasattr(self, "pattern_tree"):
            if disable_tree:
                self.pattern_tree.state(["disabled"])
            else:
                self.pattern_tree.state(["!disabled"])

    def _next_compute_job_id(self) -> int:
        self._compute_job_id += 1
        return self._compute_job_id

    def _run_compute_job(
        self,
        job_id: int,
        inputs: PalletInputs,
        options: dict,
        row_by_row_customizer,
    ) -> None:
        try:
            result = self._build_layouts(inputs, row_by_row_customizer=row_by_row_customizer, **options)
        except Exception as exc:
            logger.exception("Failed to compute layouts")
            self._compute_queue.put(("error", job_id, exc))
            return
        self._compute_queue.put(("result", job_id, inputs, result))

    def _poll_compute_results(self) -> None:
        self._compute_polling = True
        try:
            while True:
                message = self._compute_queue.get_nowait()
                if not message:
                    break
                kind, job_id, *payload = message
                if job_id != self._compute_job_id:
                    continue
                self._compute_polling = False
                if kind == "error":
                    exc = payload[0]
                    messagebox.showerror("Błąd obliczeń", str(exc))
                    self._set_compute_status("", disable_button=False, disable_tree=False)
                    return
                if kind == "result":
                    inputs, result = payload
                    self._finalize_results(inputs, result)
                    self._set_compute_status("Gotowe", disable_button=False, disable_tree=False)
                    return
        except queue.Empty:
            pass

        if self._compute_polling:
            self.after(50, self._poll_compute_results)

    def _read_inputs(self) -> PalletInputs:
        """Collect and normalize numeric values from the UI widgets."""

        inputs = PalletInputs(
            pallet_w=parse_dim(self.pallet_w_var),
            pallet_l=parse_dim(self.pallet_l_var),
            pallet_h=parse_dim(self.pallet_h_var),
            box_w=parse_dim(self.box_w_var),
            box_l=parse_dim(self.box_l_var),
            box_h=parse_dim(self.box_h_var),
            thickness=parse_dim(self.cardboard_thickness_var),
            spacing=parse_dim(self.spacing_var),
            slip_count=int(parse_dim(self.slip_count_var)),
            num_layers=int(parse_dim(self.num_layers_var)),
            max_stack=parse_dim(self.max_stack_var),
            include_pallet_height=self.include_pallet_height_var.get(),
        )

        layer_height = inputs.box_h + 2 * inputs.thickness
        if layer_height > 0:
            sync_source = getattr(self, "_layer_sync_source", "height")
            setter = getattr(self, "_set_layer_field", None)
            if sync_source == "layers":
                stack_height = compute_max_stack(
                    inputs.num_layers,
                    inputs.box_h,
                    inputs.thickness,
                    inputs.slip_count,
                    inputs.include_pallet_height,
                    inputs.pallet_h,
                )
                if stack_height > 0:
                    inputs.max_stack = stack_height
                    if setter is not None:
                        setter(self.max_stack_var, stack_height)
                    elif hasattr(self, "max_stack_var") and hasattr(
                        self.max_stack_var, "set"
                    ):
                        self.max_stack_var.set(str(stack_height))
            else:
                if inputs.max_stack > 0:
                    inputs.num_layers = compute_num_layers(
                        inputs.max_stack,
                        inputs.box_h,
                        inputs.thickness,
                        inputs.slip_count,
                        inputs.include_pallet_height,
                        inputs.pallet_h,
                    )
                    if setter is not None:
                        setter(self.num_layers_var, inputs.num_layers)
                    elif hasattr(self, "num_layers_var") and hasattr(
                        self.num_layers_var, "set"
                    ):
                        self.num_layers_var.set(str(inputs.num_layers))

        return inputs

    def _validate_inputs(self, inputs: PalletInputs) -> bool:
        """Ensure all critical dimensions are positive before computing."""

        errors = validate_pallet_inputs(inputs)
        if errors:
            messagebox.showwarning("Błąd", errors[0])
            return False
        return True

    def _read_compute_options(self) -> dict:
        """Generate layout options and best even/odd layers for the pallet."""
        try:
            min_support = parse_float(self.min_support_var.get())
        except Exception:
            min_support = 0.80
        min_support = max(0.0, min(1.0, min_support))
        try:
            result_limit = int(parse_float(self.result_limit_var.get()))
        except Exception:
            result_limit = 0
        if result_limit <= 0:
            result_limit = None

        return {
            "maximize_mixed": self.maximize_mixed.get(),
            "center_enabled": self.center_var.get(),
            "center_mode": self.center_mode_var.get(),
            "shift_even": self.shift_even_var.get(),
            "extended_library": self.extended_library_var.get(),
            "dynamic_variants": self.dynamic_variants_var.get(),
            "deep_search": self.deep_search_var.get(),
            "filter_sanity": self.filter_sanity_var.get(),
            "result_limit": result_limit,
            "allow_offsets": self.allow_offsets_var.get(),
            "min_support": min_support,
            "assume_full_support": self.assume_full_support_var.get(),
            "row_by_row_user_modified": self._row_by_row_user_modified,
            "row_by_row_vertical": self.row_by_row_vertical_var.get(),
            "row_by_row_horizontal": self.row_by_row_horizontal_var.get(),
        }

    def _build_layouts(
        self,
        inputs: PalletInputs,
        *,
        maximize_mixed: bool,
        center_enabled: bool,
        center_mode: str,
        shift_even: bool,
        row_by_row_customizer,
        extended_library: bool,
        dynamic_variants: bool,
        deep_search: bool,
        filter_sanity: bool,
        result_limit: int | None,
        allow_offsets: bool,
        min_support: float,
        assume_full_support: bool,
    ) -> LayoutComputation:
        return build_layouts(
            inputs,
            maximize_mixed=maximize_mixed,
            center_enabled=center_enabled,
            center_mode=center_mode,
            shift_even=shift_even,
            row_by_row_customizer=row_by_row_customizer,
            extended_library=extended_library,
            dynamic_variants=dynamic_variants,
            deep_search=deep_search,
            filter_sanity=filter_sanity,
            result_limit=result_limit,
            allow_offsets=allow_offsets,
            min_support=min_support,
            assume_full_support=assume_full_support,
        )

    def _finalize_results(self, inputs: PalletInputs, result: LayoutComputation) -> None:
        """Persist computed layouts and refresh dependent UI elements."""

        apply_layout_result_to_tab_state(self, inputs, result)
        self._set_row_by_row_counts(
            result.row_by_row_vertical, result.row_by_row_horizontal
        )
        raw_count = len(result.raw_layout_entries or result.layouts)
        shown_count = len(result.filtered_layout_entries or result.layouts)
        self.generated_patterns_var.set(
            f"Patterns: raw={raw_count}, shown={shown_count}"
        )
        self.update_pattern_stats()

    def draw_pallet(self, draw_idle: bool = False):
        pallet_w = parse_dim(self.pallet_w_var)
        pallet_l = parse_dim(self.pallet_l_var)
        axes = [self.ax_odd, self.ax_even, self.ax_overlay]
        labels = ["Warstwa nieparzysta", "Warstwa parzysta", "Nakładanie"]
        self.patches = [[] for _ in axes[:2]]
        for idx, ax in enumerate(axes):
            ax.clear()
            ax.add_patch(
                plt.Rectangle(
                    (0, 0),
                    pallet_w,
                    pallet_l,
                    fill=False,
                    edgecolor="black",
                    linewidth=2,
                )
            )
            if idx < 2 and idx < len(self.layers):
                # Always apply the stored transformation when drawing so the
                # visual representation matches the selected mirror option.
                coords = self.apply_transformation(
                    list(self.layers[idx]),
                    self.transformations[idx],
                    pallet_w,
                    pallet_l,
                )
                collision_idx = self.detect_collisions(coords, pallet_w, pallet_l)
                for i, (x, y, w, h) in enumerate(coords):
                    base_color = "blue" if idx == 0 else "green"
                    color = "red" if i in collision_idx else base_color
                    patch = plt.Rectangle(
                        (x, y),
                        w,
                        h,
                        fill=True,
                        facecolor=color,
                        alpha=0.5,
                        edgecolor="black",
                    )
                    ax.add_patch(patch)
                    self.patches[idx].append((patch, i))
                    if self.show_numbers_var.get():
                        ax.text(
                            x + w / 2,
                            y + h / 2,
                            str(
                                self.carton_ids[idx][i]
                                if idx < len(self.carton_ids)
                                and i < len(self.carton_ids[idx])
                                else i + 1
                            ),
                            ha="center",
                            va="center",
                            fontsize=8,
                            color="black",
                            zorder=10,
                        )
                ax.set_title(f"{labels[idx]}: {len(self.layers[idx])}")
            elif idx == 2:
                if self.layers:
                    coords = self.apply_transformation(
                        list(self.layers[0]),
                        self.transformations[0],
                        pallet_w,
                        pallet_l,
                    )
                    for x, y, w, h in coords:
                        ax.add_patch(
                            plt.Rectangle(
                                (x, y),
                                w,
                                h,
                                fill=True,
                                facecolor="blue",
                                alpha=0.5,
                                edgecolor="black",
                            )
                        )
                if len(self.layers) > 1:
                    coords = self.apply_transformation(
                        list(self.layers[1]),
                        self.transformations[1],
                        pallet_w,
                        pallet_l,
                    )
                    for x, y, w, h in coords:
                        ax.add_patch(
                            plt.Rectangle(
                                (x, y),
                                w,
                                h,
                                fill=True,
                                facecolor="green",
                                alpha=0.5,
                                edgecolor="black",
                            )
                        )
                ax.set_title(labels[idx])
            ax.set_xlim(-50, pallet_w + 50)
            ax.set_ylim(-50, pallet_l + 50)
            ax.set_aspect("equal")
        if draw_idle:
            self.canvas.draw_idle()
        else:
            self.canvas.draw()
        if hasattr(self, "status_var"):
            self.status_var.set("")
        if hasattr(self, "compute_btn"):
            self.compute_btn.state(["!disabled"])
        self.highlight_selection()

    def highlight_selection(self):
        """Visually highlight currently selected cartons."""
        for layer_idx, patch_list in enumerate(self.patches):
            for patch, idx in patch_list:
                if (layer_idx, idx) in self.selected_indices:
                    patch.set_edgecolor("orange")
                    patch.set_linewidth(2)
                else:
                    patch.set_edgecolor("black")
                    patch.set_linewidth(1)
        self.canvas.draw_idle()

    def sort_layers(self):
        """Sort cartons within each layer for consistent numbering."""
        new_sel = set()
        current_selection = self.editor_controller.selected_pairs()
        for layer_idx, layer in enumerate(self.layers):
            order = sorted(range(len(layer)), key=lambda i: (layer[i][1], layer[i][0]))
            if order != list(range(len(layer))):
                self.layers[layer_idx] = [layer[i] for i in order]
                self.carton_ids[layer_idx] = [self.carton_ids[layer_idx][i] for i in order]
                mapping = {old_idx: new_idx for new_idx, old_idx in enumerate(order)}
            else:
                mapping = {i: i for i in range(len(layer))}
            for l_idx, idx in current_selection:
                if l_idx == layer_idx:
                    new_sel.add((l_idx, mapping.get(idx, idx)))
                else:
                    new_sel.add((l_idx, idx))
        self._set_selection_pairs(new_sel)

    def renumber_layer(self, layer_idx):
        """Assign sequential carton numbers to the chosen layer."""
        if layer_idx < len(self.carton_ids):
            self.carton_ids[layer_idx] = list(range(1, len(self.layers[layer_idx]) + 1))

    def renumber_layers(self):
        for idx in range(len(self.layers)):
            self.renumber_layer(idx)
        
    def toggle_edit_mode(self):
        if self.modify_mode_var.get():
            if hasattr(self, "status_var"):
                self.status_var.set(
                    "Tryb edycji: lewy przycisk \u2013 przesuwaj, "
                    "SHIFT+klik \u2013 wyb\u00f3r wielu, prawy \u2013 menu"
                )
            self.press_cid = self.canvas.mpl_connect(
                "button_press_event", self.on_press
            )
            self.motion_cid = self.canvas.mpl_connect(
                "motion_notify_event", self.on_motion
            )
            self.release_cid = self.canvas.mpl_connect(
                "button_release_event", self.on_release
            )
            self.key_cid = self.canvas.mpl_connect(
                "key_press_event", self.on_key_press
            )
            if self.editor_controller.active_layer is None:
                self.editor_controller.active_layer = 0
        else:
            for cid in [self.press_cid, self.motion_cid, self.release_cid]:
                if cid is not None:
                    self.canvas.mpl_disconnect(cid)
            self.press_cid = self.motion_cid = self.release_cid = None
            if self.key_cid is not None:
                self.canvas.mpl_disconnect(self.key_cid)
            self.key_cid = None
            self._clear_selection()
            self.editor_controller = EditorController()
            self.drag_info = None
            self.drag_button = None
            self.drag_select_origin = None
            self.drag_snapshot_saved = False
            self.draw_pallet()
            if hasattr(self, "status_var"):
                self.status_var.set("")

    def _toolbar_busy(self) -> bool:
        toolbar = getattr(self, "toolbar", None)
        if toolbar is None:
            return False
        mode = getattr(toolbar, "mode", "") or ""
        active = getattr(toolbar, "_active", "") or ""
        return bool(mode) or bool(active)

    def on_press(self, event):
        if not self.modify_mode_var.get() or event.inaxes not in [
            self.ax_odd,
            self.ax_even,
        ]:
            return
        if TabPallet._toolbar_busy(self):
            return
        if event.button not in (1, 3):
            return
        layer_idx = 0 if event.inaxes is self.ax_odd else 1
        if event.xdata is not None and event.ydata is not None:
            self.context_layer = layer_idx
            self.context_pos = (event.xdata, event.ydata)
        if event.xdata is None or event.ydata is None:
            return

        hit_index = None
        for patch, idx in self.patches[layer_idx]:
            contains, _ = patch.contains(event)
            if contains:
                hit_index = idx
                break

        ctrl = self._ctrl_active(event)
        shift = self._shift_active(event)
        self.editor_controller.on_press(
            layer_idx,
            hit_index,
            event.button,
            ctrl,
            shift,
            event.xdata,
            event.ydata,
        )
        self._sync_selection_from_controller()

        self.drag_snapshot_saved = False
        if event.button == 3:
            self.on_right_click(event)
        self.highlight_selection()

    def _request_redraw(self) -> None:
        self._redraw_pending = True
        if self._redraw_timer is None:
            self._redraw_timer = self.after(16, self._flush_redraw)

    def _flush_redraw(self) -> None:
        self._redraw_timer = None
        if self._redraw_pending:
            self.canvas.draw_idle()
            self._redraw_pending = False

    def on_motion(self, event):
        if event.xdata is None or event.ydata is None:
            return
        if TabPallet._toolbar_busy(self):
            return
        result = self.editor_controller.on_motion(event.xdata, event.ydata)
        if not result or not self.editor_controller.is_dragging:
            return
        active_layer = self.editor_controller.active_layer
        if active_layer is None:
            return
        selection = filter_selection_for_layer(self.selected_indices, active_layer)
        if not selection:
            return

        pallet_w = parse_dim(self.pallet_w_var)
        pallet_l = parse_dim(self.pallet_l_var)

        if not self.drag_snapshot_saved:
            TabPallet._record_state(self)
            self.drag_snapshot_saved = True

        dx, dy = result["delta"]
        layers_to_check = set()
        for layer_idx, idx in list(selection):
            if layer_idx >= len(self.layers) or idx >= len(self.layers[layer_idx]):
                continue
            for patch, j in self.patches[layer_idx]:
                if j != idx:
                    continue
                new_x = patch.get_x() + dx
                new_y = patch.get_y() + dy
                patch.set_xy((new_x, new_y))
                x, y, w, h = self.layers[layer_idx][idx]
                orig_x, orig_y, _, _ = self.inverse_transformation(
                    [(new_x, new_y, w, h)],
                    self.transformations[layer_idx],
                    pallet_w,
                    pallet_l,
                )[0]
                self.layers[layer_idx][idx] = (orig_x, orig_y, w, h)
                layers_to_check.add(layer_idx)
                if self.layers_linked():
                    other_layer = 1 - layer_idx
                    if (
                        other_layer < len(self.layers)
                        and idx < len(self.layers[other_layer])
                        and self.layer_patterns[other_layer] == self.layer_patterns[layer_idx]
                    ):
                        self.layers[other_layer][idx] = (orig_x, orig_y, w, h)
                        layers_to_check.add(other_layer)
                        for p, j2 in self.patches[other_layer]:
                            if j2 == idx:
                                tx, ty, tw, th = self.apply_transformation(
                                    [(orig_x, orig_y, w, h)],
                                    self.transformations[other_layer],
                                    pallet_w,
                                    pallet_l,
                                )[0]
                                p.set_xy((tx, ty))
                                p.set_width(tw)
                                p.set_height(th)
                                break
                break

        if self.layers_linked():
            layers_to_check |= {
                1 - idx for idx in layers_to_check if 1 - idx < len(self.layers)
            }
        for layer_idx in layers_to_check:
            coords = self.apply_transformation(
                list(self.layers[layer_idx]),
                self.transformations[layer_idx],
                pallet_w,
                pallet_l,
            )
            collision_idx = self.detect_collisions(coords, pallet_w, pallet_l)
            for p, i in self.patches[layer_idx]:
                base_color = "blue" if layer_idx == 0 else "green"
                color = "red" if i in collision_idx else base_color
                p.set_facecolor(color)

        self._request_redraw()

    def on_release(self, event):
        if TabPallet._toolbar_busy(self):
            return
        if event is None:
            items = []
            if self.drag_info is not None:
                items = self.drag_info if isinstance(self.drag_info, list) else [self.drag_info]
            if not items:
                return
            pallet_w = parse_dim(self.pallet_w_var)
            pallet_l = parse_dim(self.pallet_l_var)
            for layer_idx, idx, patch, *_ in items:
                selection = filter_selection_for_layer(self.selected_indices, layer_idx)
                new_x, new_y = patch.get_xy()
                x, y, w, h = self.layers[layer_idx][idx]
                orig_x, orig_y, _, _ = self.inverse_transformation(
                    [(new_x, new_y, w, h)],
                    self.transformations[layer_idx],
                    pallet_w,
                    pallet_l,
                )[0]
                other_boxes = [
                    b
                    for j, b in enumerate(self.layers[layer_idx])
                    if j != idx or (layer_idx, j) not in selection
                ]
                snap_x, snap_y = self.snap_position(
                    orig_x, orig_y, w, h, pallet_w, pallet_l, other_boxes
                )
                self.layers[layer_idx][idx] = (snap_x, snap_y, w, h)
                other_layer = 1 - layer_idx
                if (
                    other_layer < len(self.layers)
                    and idx < len(self.layers[other_layer])
                    and self.layer_patterns[other_layer] == self.layer_patterns[layer_idx]
                    and self.layers_linked()
                ):
                    self.layers[other_layer][idx] = (snap_x, snap_y, w, h)
            getattr(self, "sort_layers", lambda: None)()
            self.draw_pallet()
            self.update_summary()
            self.highlight_selection()
            return
        if event.xdata is None or event.ydata is None:
            return
        editor_controller = getattr(self, "editor_controller", None)
        if editor_controller is None:
            return
        result = editor_controller.on_release(event.button, event.xdata, event.ydata)
        if not result.get("was_dragging"):
            self.drag_snapshot_saved = False
            return

        pallet_w = parse_dim(self.pallet_w_var)
        pallet_l = parse_dim(self.pallet_l_var)

        selection = self._selection_for_active_layer()
        for layer_idx, idx in list(selection):
            if layer_idx >= len(self.layers) or idx >= len(self.layers[layer_idx]):
                continue
            patch = next((p for p, j in self.patches[layer_idx] if j == idx), None)
            if patch is None:
                continue
            new_x, new_y = patch.get_xy()
            x, y, w, h = self.layers[layer_idx][idx]
            orig_x, orig_y, _, _ = self.inverse_transformation(
                [(new_x, new_y, w, h)],
                self.transformations[layer_idx],
                pallet_w,
                pallet_l,
            )[0]
            other_boxes = [
                b
                for j, b in enumerate(self.layers[layer_idx])
                if j != idx or (layer_idx, j) not in selection
            ]
            snap_x, snap_y = self.snap_position(
                orig_x, orig_y, w, h, pallet_w, pallet_l, other_boxes
            )
            self.layers[layer_idx][idx] = (snap_x, snap_y, w, h)
            other_layer = 1 - layer_idx
            if (
                other_layer < len(self.layers)
                and idx < len(self.layers[other_layer])
                and self.layer_patterns[other_layer] == self.layer_patterns[layer_idx]
                and self.layers_linked()
            ):
                self.layers[other_layer][idx] = (snap_x, snap_y, w, h)

        self.drag_snapshot_saved = False
        getattr(self, "sort_layers", lambda: None)()
        self.draw_pallet()
        self.update_summary()
        self.highlight_selection()

    def insert_carton(self, layer_idx, pos):
        """Insert a carton into the given layer at `pos`."""
        TabPallet._record_state(self)
        thickness = parse_dim(self.cardboard_thickness_var)
        if self.layers[layer_idx]:
            _, _, w, h = self.layers[layer_idx][0]
        else:
            w = parse_dim(self.box_w_var) + 2 * thickness
            h = parse_dim(self.box_l_var) + 2 * thickness
        self.layers[layer_idx].append((pos[0], pos[1], w, h))
        next_id = max(self.carton_ids[layer_idx], default=0) + 1
        self.carton_ids[layer_idx].append(next_id)
        other_layer = 1 - layer_idx
        if (
            other_layer < len(self.layers)
            and self.layer_patterns[other_layer] == self.layer_patterns[layer_idx]
            and self.layers_linked()
        ):
            self.layers[other_layer].append((pos[0], pos[1], w, h))
            next_id_other = max(self.carton_ids[other_layer], default=0) + 1
            self.carton_ids[other_layer].append(next_id_other)
        getattr(self, "sort_layers", lambda: None)()
        self.renumber_layer(layer_idx)
        if other_layer < len(self.layers) and self.layers_linked() and self.layer_patterns[other_layer] == self.layer_patterns[layer_idx]:
            self.renumber_layer(other_layer)
        self.draw_pallet()
        self.update_summary()

    def insert_carton_button(self):
        self.insert_carton(self.context_layer, self.context_pos)

    def delete_selected_carton(self):
        """Delete all currently selected cartons."""
        selection = self._selection_for_active_layer()
        if not selection:
            return

        TabPallet._record_state(self)
        affected = set()
        for layer_idx, idx in sorted(
            selection, key=lambda t: (t[0], -t[1])
        ):
            if layer_idx >= len(self.layers) or idx >= len(self.layers[layer_idx]):
                continue
            del self.layers[layer_idx][idx]
            del self.carton_ids[layer_idx][idx]
            other_layer = 1 - layer_idx
            affected.add(layer_idx)
            if (
                other_layer < len(self.layers)
                and idx < len(self.layers[other_layer])
                and self.layer_patterns[other_layer] == self.layer_patterns[layer_idx]
                and self.layers_linked()
            ):
                del self.layers[other_layer][idx]
                del self.carton_ids[other_layer][idx]
                affected.add(other_layer)

        for idx in affected:
            self.renumber_layer(idx)

        self._clear_selection()
        self.drag_info = None
        getattr(self, "sort_layers", lambda: None)()
        self.draw_pallet()
        self.update_summary()
        self.highlight_selection()

    def rotate_selected_carton(self):
        """Rotate all selected cartons by 90° around their centers."""
        selection = self._selection_for_active_layer()
        if not selection:
            return

        TabPallet._record_state(self)
        for layer_idx, idx in list(selection):
            if layer_idx >= len(self.layers) or idx >= len(self.layers[layer_idx]):
                continue
            x, y, w, h = self.layers[layer_idx][idx]

            center_x = x + w / 2
            center_y = y + h / 2
            w, h = h, w
            x = center_x - w / 2
            y = center_y - h / 2

            self.layers[layer_idx][idx] = (x, y, w, h)
            other_layer = 1 - layer_idx
            if (
                other_layer < len(self.layers)
                and idx < len(self.layers[other_layer])
                and self.layer_patterns[other_layer] == self.layer_patterns[layer_idx]
                and self.layers_linked()
            ):
                self.layers[other_layer][idx] = (x, y, w, h)
        getattr(self, "sort_layers", lambda: None)()
        self.draw_pallet()
        self.update_summary()

    @staticmethod
    def _find_axis_limits(boxes, indices, axis, pallet_extent):
        if not indices:
            return 0.0, pallet_extent

        selected = [boxes[i] for i in indices]
        tol = 1e-6
        if axis == "x":
            coord_min = min(x for x, y, w, h in selected)
            coord_max = max(x + w for x, y, w, h in selected)
            perp_min = min(y for x, y, w, h in selected)
            perp_max = max(y + h for x, y, w, h in selected)
            lower_candidates = [0.0]
            upper_candidates = [pallet_extent]
            for j, (bx, by, bw, bh) in enumerate(boxes):
                if j in indices:
                    continue
                if by >= perp_max - tol or by + bh <= perp_min + tol:
                    continue
                left_edge = bx + bw
                right_edge = bx
                if left_edge <= coord_min + tol:
                    lower_candidates.append(left_edge)
                if right_edge >= coord_max - tol:
                    upper_candidates.append(right_edge)
            return max(lower_candidates), min(upper_candidates)

        coord_min = min(y for x, y, w, h in selected)
        coord_max = max(y + h for x, y, w, h in selected)
        perp_min = min(x for x, y, w, h in selected)
        perp_max = max(x + w for x, y, w, h in selected)
        lower_candidates = [0.0]
        upper_candidates = [pallet_extent]
        for j, (bx, by, bw, bh) in enumerate(boxes):
            if j in indices:
                continue
            if bx >= perp_max - tol or bx + bw <= perp_min + tol:
                continue
            bottom_edge = by + bh
            top_edge = by
            if bottom_edge <= coord_min + tol:
                lower_candidates.append(bottom_edge)
            if top_edge >= coord_max - tol:
                upper_candidates.append(top_edge)
        return max(lower_candidates), min(upper_candidates)

    def _distribute(self, layer_idx, indices, start, end, orientation):
        boxes = self.layers[layer_idx]
        sizes = [boxes[i][2 if orientation == "x" else 3] for i in indices]
        total = sum(sizes)
        available = end - start
        if total > available:
            return
        gap = max((available - total) / (len(indices) + 1), 0)
        pos = start + gap
        for i, size in zip(sorted(indices), sizes):
            x, y, w, h = boxes[i]
            if orientation == "x":
                x = pos
                pos += size + gap
            else:
                y = pos
                pos += size + gap
            boxes[i] = (x, y, w, h)
        other_layer = 1 - layer_idx
        if (
            other_layer < len(self.layers)
            and self.layer_patterns[other_layer] == self.layer_patterns[layer_idx]
            and self.layers_linked()
        ):
            for i in indices:
                if i < len(self.layers[other_layer]):
                    self.layers[other_layer][i] = self.layers[layer_idx][i]

    def distribute_selected_edges(self):
        selection = self._selection_for_active_layer()
        if not selection:
            return

        layer_idx = next(iter(selection))[0]
        indices = [i for layer, i in selection if layer == layer_idx]
        if not indices:
            return

        TabPallet._record_state(self)
        pallet_w = parse_dim(self.pallet_w_var)
        pallet_l = parse_dim(self.pallet_l_var)
        sel = [self.layers[layer_idx][i] for i in indices]
        span_x = max(x + w for x, y, w, h in sel) - min(x for x, y, w, h in sel)
        span_y = max(y + h for x, y, w, h in sel) - min(y for x, y, w, h in sel)
        orientation = "x" if span_x >= span_y else "y"
        boxes = self.layers[layer_idx]
        start, end = TabPallet._find_axis_limits(
            boxes,
            indices,
            orientation,
            pallet_w if orientation == "x" else pallet_l,
        )
        if end - start <= 0:
            return
        TabPallet._distribute(self, layer_idx, indices, start, end, orientation)
        getattr(self, "sort_layers", lambda: None)()
        self.draw_pallet()
        self.update_summary()
        self.highlight_selection()

    def auto_space_selected(self):
        selection = self._selection_for_active_layer()
        if not selection:
            return

        layer_idx = next(iter(selection))[0]
        indices = [i for layer, i in selection if layer == layer_idx]
        if not indices:
            return

        TabPallet._record_state(self)
        pallet_w = parse_dim(self.pallet_w_var)
        pallet_l = parse_dim(self.pallet_l_var)
        boxes = self.layers[layer_idx]
        sel_boxes = [boxes[i] for i in indices]
        min_x = min(x for x, y, w, h in sel_boxes)
        max_x = max(x + w for x, y, w, h in sel_boxes)
        min_y = min(y for x, y, w, h in sel_boxes)
        max_y = max(y + h for x, y, w, h in sel_boxes)

        left_candidates = [0] + [
            bx + bw
            for j, (bx, by, bw, bh) in enumerate(boxes)
            if j not in indices and bx + bw <= min_x
        ]
        right_candidates = [pallet_w] + [
            bx
            for j, (bx, by, bw, bh) in enumerate(boxes)
            if j not in indices and bx >= max_x
        ]
        bottom_candidates = [0] + [
            by + bh
            for j, (bx, by, bw, bh) in enumerate(boxes)
            if j not in indices and by + bh <= min_y
        ]
        top_candidates = [pallet_l] + [
            by
            for j, (bx, by, bw, bh) in enumerate(boxes)
            if j not in indices and by >= max_y
        ]
        left = max(left_candidates)
        right = min(right_candidates)
        bottom = max(bottom_candidates)
        top = min(top_candidates)

        span_x = max_x - min_x
        span_y = max_y - min_y
        orientation = "x" if span_x >= span_y else "y"
        start = left
        end = right if orientation == "x" else top
        if orientation == "y":
            start = bottom
            end = top
        self._distribute(layer_idx, indices, start, end, orientation)
        getattr(self, "sort_layers", lambda: None)()
        self.draw_pallet()
        self.update_summary()
        self.highlight_selection()

    def distribute_selected_between(self):
        selection = self._selection_for_active_layer()
        if not selection:
            return

        layer_idx = next(iter(selection))[0]
        indices = [i for layer, i in selection if layer == layer_idx]
        if not indices:
            return

        TabPallet._record_state(self)
        pallet_w = parse_dim(self.pallet_w_var)
        pallet_l = parse_dim(self.pallet_l_var)
        boxes = self.layers[layer_idx]
        sel_boxes = [boxes[i] for i in indices]
        min_x = min(x for x, y, w, h in sel_boxes)
        max_x = max(x + w for x, y, w, h in sel_boxes)
        min_y = min(y for x, y, w, h in sel_boxes)
        max_y = max(y + h for x, y, w, h in sel_boxes)

        left_candidates = [0] + [
            bx + bw
            for j, (bx, by, bw, bh) in enumerate(boxes)
            if j not in indices and bx + bw <= min_x
        ]
        right_candidates = [pallet_w] + [
            bx
            for j, (bx, by, bw, bh) in enumerate(boxes)
            if j not in indices and bx >= max_x
        ]
        bottom_candidates = [0] + [
            by + bh
            for j, (bx, by, bw, bh) in enumerate(boxes)
            if j not in indices and by + bh <= min_y
        ]
        top_candidates = [pallet_l] + [
            by
            for j, (bx, by, bw, bh) in enumerate(boxes)
            if j not in indices and by >= max_y
        ]
        left = max(left_candidates)
        right = min(right_candidates)
        bottom = max(bottom_candidates)
        top = min(top_candidates)

        span_x = max_x - min_x
        span_y = max_y - min_y
        orientation = "x" if span_x >= span_y else "y"
        start = left
        end = right if orientation == "x" else top
        if orientation == "y":
            start = bottom
            end = top
        TabPallet._distribute(self, layer_idx, indices, start, end, orientation)
        getattr(self, "sort_layers", lambda: None)()
        self.draw_pallet()
        self.update_summary()

    def distribute_selected_long_side(self):
        selection = self._selection_for_active_layer()
        if not selection:
            return

        layer_idx = next(iter(selection))[0]
        indices = [i for layer, i in selection if layer == layer_idx]
        if not indices:
            return

        TabPallet._record_state(self)
        pallet_w = parse_dim(self.pallet_w_var)
        pallet_l = parse_dim(self.pallet_l_var)
        boxes = self.layers[layer_idx]
        orientation = "x" if pallet_w >= pallet_l else "y"
        extent = pallet_w if orientation == "x" else pallet_l
        start, end = TabPallet._find_axis_limits(boxes, indices, orientation, extent)
        if end - start <= 0:
            return
        self._distribute(layer_idx, indices, start, end, orientation)
        getattr(self, "sort_layers", lambda: None)()
        self.draw_pallet()
        self.update_summary()
        self.highlight_selection()

    def center_selected_cartons(self):
        selection = self._selection_for_active_layer()
        if not selection:
            return

        layer_idx = next(iter(selection))[0]
        indices = [i for layer, i in selection if layer == layer_idx]
        if not indices:
            return

        TabPallet._record_state(self)
        pallet_w = parse_dim(self.pallet_w_var)
        pallet_l = parse_dim(self.pallet_l_var)
        boxes = self.layers[layer_idx]
        selected = [boxes[i] for i in indices]
        min_x = min(x for x, y, w, h in selected)
        max_x = max(x + w for x, y, w, h in selected)
        min_y = min(y for x, y, w, h in selected)
        max_y = max(y + h for x, y, w, h in selected)

        left, right = TabPallet._find_axis_limits(boxes, indices, "x", pallet_w)
        bottom, top = TabPallet._find_axis_limits(boxes, indices, "y", pallet_l)

        available_x = right - left
        available_y = top - bottom
        width = max_x - min_x
        height = max_y - min_y
        if available_x <= 0 or available_y <= 0:
            return
        if width > available_x + 1e-6 or height > available_y + 1e-6:
            return

        offset_x = (left + available_x / 2) - (min_x + width / 2)
        offset_y = (bottom + available_y / 2) - (min_y + height / 2)

        for i in indices:
            x, y, w, h = boxes[i]
            boxes[i] = (x + offset_x, y + offset_y, w, h)

        other_layer = 1 - layer_idx
        if (
            other_layer < len(self.layers)
            and self.layer_patterns[other_layer] == self.layer_patterns[layer_idx]
            and self.layers_linked()
        ):
            for i in indices:
                if i < len(self.layers[other_layer]):
                    x, y, w, h = self.layers[layer_idx][i]
                    self.layers[other_layer][i] = (x, y, w, h)

        getattr(self, "sort_layers", lambda: None)()
        self.draw_pallet()
        self.update_summary()
        self.highlight_selection()

    def on_right_click(self, event):
        if not self.modify_mode_var.get() or event.inaxes not in [
            self.ax_odd,
            self.ax_even,
        ]:
            return
        self.context_layer = 0 if event.inaxes is self.ax_odd else 1
        if event.xdata is not None and event.ydata is not None:
            self.context_pos = (event.xdata, event.ydata)

        if self.context_menu is None:
            self.context_menu = tk.Menu(self, tearoff=0)
            self.context_menu.add_command(
                label="Wstaw karton", command=self.insert_carton_button
            )
            self.context_menu.add_command(
                label="Usu\u0144 zaznaczone", command=self.delete_selected_carton
            )
            self.context_menu.add_command(
                label="Obróć zaznaczone 90°", command=self.rotate_selected_carton
            )
            self.context_menu.add_command(
                label="R\u00f3wnomiernie wzd\u0142u\u017c boku palety",
                command=self.distribute_selected_edges,
            )
            self.context_menu.add_command(
                label="R\u00f3wnomiernie wzd\u0142u\u017c d\u0142u\u017cszego boku",
                command=self.distribute_selected_long_side,
            )
            self.context_menu.add_command(
                label="R\u00f3wnomiernie wzd\u0142u\u017c innych karton\u00f3w",
                command=self.distribute_selected_between,
            )
            self.context_menu.add_command(
                label="Automatyczny odst\u0119p", command=self.auto_space_selected
            )
            self.context_menu.add_command(
                label="Wycentruj zaznaczone",
                command=self.center_selected_cartons,
            )

        state = "normal" if self._selection_for_active_layer() else "disabled"
        last_index = self.context_menu.index("end") or 0
        for i in range(1, last_index + 1):
            self.context_menu.entryconfigure(i, state=state)
        gui_ev = event.guiEvent
        if gui_ev:
            self.context_menu.tk_popup(int(gui_ev.x_root), int(gui_ev.y_root))
        self.highlight_selection()

    def update_summary(self):
        self._debug_log_call("update_summary")
        if not self.layers:
            self.totals_label.config(text="")
            self.materials_label.config(text="")
            self.mass_label.config(text="")
            self.limit_label.config(text="")
            self.area_label.config(text="")
            self.clearance_label.config(text="")
            self.solution_catalog = SolutionCatalog.empty()
            self.solution_by_key = {}
            self.best_layout_key = ""
            if hasattr(self, "pattern_tree"):
                for item in self.pattern_tree.get_children():
                    self.pattern_tree.delete(item)
            if hasattr(self, "pattern_detail_var"):
                self.pattern_detail_var.set("")
            return

        pallet_w = parse_dim(self.pallet_w_var)
        pallet_l = parse_dim(self.pallet_l_var)
        pallet_h = parse_dim(self.pallet_h_var)
        box_w = parse_dim(self.box_w_var)
        box_l = parse_dim(self.box_l_var)
        box_h = parse_dim(self.box_h_var)
        thickness = parse_dim(self.cardboard_thickness_var)
        num_layers = getattr(self, "num_layers", int(parse_dim(self.num_layers_var)))
        box_h_ext = box_h + 2 * thickness
        cartons_per_odd = len(self.layers[0]) if self.layers else 0
        cartons_per_even = (
            len(self.layers[1]) if len(self.layers) > 1 else cartons_per_odd
        )
        total_cartons = sum(
            cartons_per_odd if i % 2 == 1 else cartons_per_even
            for i in range(1, num_layers + 1)
        )
        total_products = total_cartons * self._get_products_per_carton()
        stack_height = num_layers * box_h_ext
        if self.include_pallet_height_var.get():
            stack_height += pallet_h

        longer_side = max(box_w, box_l)
        self.tape_per_carton = 2 * (longer_side + box_h) / 1000
        self.film_per_pallet = 2 * (pallet_w + pallet_l) / 1000 * 6
        total_tape = total_cartons * self.tape_per_carton

        self.totals_label.config(
            text=f"Kartonów: {total_cartons} | Produkty: {total_products} | Wysokość: {stack_height:.1f} mm"
        )
        self.materials_label.config(
            text=f"Taśma: {total_tape:.2f} m | Folia: {self.film_per_pallet:.2f} m"
        )
        carton_wt, weight_source = self._get_active_carton_weight()
        source_label = "ręczna" if weight_source == "manual" else "z bazy"
        carrier_mass = self.pallet_base_mass
        total_mass = carton_wt * total_cartons + carrier_mass
        self.mass_label.config(
            text=(
                f"Masa kartonu ({source_label}): {carton_wt:.2f} kg | "
                f"Masa nośnika: {carrier_mass:.2f} kg | Masa palety: {total_mass:.2f} kg"
            )
        )

        limit_message = ""
        if total_mass > 600:
            excess = total_mass - 600
            limit_message = f"Przekroczono limit 600 kg o {excess:.2f} kg."
            if carton_wt > 0 and total_cartons > 0:
                remove_cartons = math.ceil(excess / carton_wt)
                remove_cartons = min(remove_cartons, total_cartons)
                limit_message += f" Należy zdjąć {remove_cartons} kartonów."
                removed_layers = 0
                removed_cartons = 0
                suggested_layers = 0
                for layer_index in range(num_layers, 0, -1):
                    layer_cartons = (
                        cartons_per_even if layer_index % 2 == 0 else cartons_per_odd
                    )
                    removed_layers += 1
                    removed_cartons += layer_cartons
                    if removed_cartons >= remove_cartons:
                        suggested_layers = max(num_layers - removed_layers, 0)
                        break
                else:
                    suggested_layers = 0
                limit_message += f" Sugerowana liczba warstw: {suggested_layers}."
            else:
                limit_message += " Brak danych o masie kartonu do wyliczeń."
        self.limit_label.config(text=limit_message)

        pallet_area = pallet_w * pallet_l / 1_000_000
        carton_area = (box_w + 2 * thickness) * (box_l + 2 * thickness) / 1_000_000
        area_ratio = pallet_area / carton_area if carton_area > 0 else 0
        self.area_label.config(
            text=(
                f"Pow. palety: {pallet_area:.3f} m² | "
                f"Pow. kartonu: {carton_area:.3f} m² | Miejsca: {area_ratio:.2f}"
            )
        )

        clearance_stats = self._edge_clearance_stats(pallet_w, pallet_l)
        if clearance_stats:
            (long_value, long_layer, long_carton), (
                short_value,
                short_layer,
                short_carton,
            ) = clearance_stats

            clearance_text = (
                "Dłuższy bok: "
                f"{long_value:.1f} mm (w {long_layer}, k {long_carton}) | "
                f"Krótszy bok: {short_value:.1f} mm (w {short_layer}, k {short_carton})"
            )
        else:
            clearance_text = ""

        self.clearance_label.config(text=clearance_text)

    def _edge_clearance_stats(self, pallet_w: float, pallet_l: float):
        if not self.layers or pallet_w <= 0 or pallet_l <= 0:
            return None

        long_axis = "x" if pallet_w >= pallet_l else "y"
        min_long = min_short = None

        def update_stat(current, value, layer_idx, carton_id, comparator):
            if current is None or comparator(value, current[0]):
                return (value, layer_idx + 1, carton_id)
            return current

        for layer_idx, boxes in enumerate(self.layers):
            transform = "Brak"
            if layer_idx < len(self.transformations):
                transform = self.transformations[layer_idx] or "Brak"

            coords = TabPallet.apply_transformation(boxes, transform, pallet_w, pallet_l)
            ids = (
                self.carton_ids[layer_idx]
                if layer_idx < len(self.carton_ids)
                else list(range(1, len(coords) + 1))
            )

            for i, (x, y, w, h) in enumerate(coords):
                carton_id = ids[i] if i < len(ids) else i + 1
                clearance_x = min(x, pallet_w - (x + w))
                clearance_y = min(y, pallet_l - (y + h))

                long_clearance = clearance_x if long_axis == "x" else clearance_y
                short_clearance = clearance_y if long_axis == "x" else clearance_x

                min_long = update_stat(min_long, long_clearance, layer_idx, carton_id, lambda a, b: a < b)
                min_short = update_stat(
                    min_short, short_clearance, layer_idx, carton_id, lambda a, b: a < b
                )

        if None in (min_long, min_short):
            return None

        return min_long, min_short

    def update_pattern_stats(self):
        self._debug_log_call("update_pattern_stats")
        if not hasattr(self, "pattern_tree"):
            return

        previous_flag = getattr(self, "_suspend_pattern_apply", False)
        target_key = ""
        self._suspend_pattern_apply = True
        try:
            self.pattern_tree.state(["disabled"])
            previous_selection = self.pattern_tree.selection()
            for item in self.pattern_tree.get_children():
                self.pattern_tree.delete(item)

            catalog = getattr(self, "solution_catalog", None)
            if not catalog or not catalog.solutions:
                if hasattr(self, "pattern_detail_var"):
                    self.pattern_detail_var.set("")
                return

            for solution in catalog.solutions:
                metrics = solution.metrics
                instability_risk = metrics.get("instability_risk", 0.0) > 0.5
                values = (
                    solution.display,
                    str(int(metrics.get("cartons", 0))),
                    f"{metrics.get('stability', 0.0) * 100:.1f}",
                    f"{metrics.get('layer_eff', 0.0) * 100:.1f}",
                    f"{metrics.get('cube_eff', 0.0) * 100:.1f}",
                    f"{metrics.get('support_fraction', 0.0) * 100:.1f}",
                    f"{metrics.get('min_support', 0.0) * 100:.1f}",
                    f"{metrics.get('edge_contact', 0.0) * 100:.1f}",
                    f"{metrics.get('min_edge_clearance', 0.0):.1f}",
                    str(int(metrics.get("grip_changes", 0))),
                    "Tak" if instability_risk else "Nie",
                )
                self.pattern_tree.insert("", "end", iid=solution.key, values=values)

            target_key = ""
            if previous_selection:
                prev = previous_selection[0]
                if prev in catalog.by_key:
                    target_key = prev
            if not target_key:
                for key in catalog.standard_order:
                    if key in catalog.by_key:
                        target_key = key
                        break
            if not target_key and catalog.solutions:
                target_key = catalog.solutions[0].key
            if target_key:
                self.pattern_tree.selection_set(target_key)
                self.pattern_tree.see(target_key)
                self._update_pattern_detail_only(target_key)
        finally:
            self._suspend_pattern_apply = previous_flag
            self.pattern_tree.state(["!disabled"])
        if target_key:
            self._request_apply(target_key, force=True, reason="PostRebuild")

    def _pattern_tree_disabled(self) -> bool:
        try:
            return self.pattern_tree.instate(["disabled"])
        except Exception:
            return False

    def _request_apply(self, key: str, *, force: bool, reason: str = "") -> None:
        if not key:
            return
        self._pending_key = key
        self._pending_force = self._pending_force or force
        if getattr(self, "_suspend_pattern_apply", False) or self._pattern_tree_disabled():
            return
        if self._apply_after_id is not None:
            self.after_cancel(self._apply_after_id)
        self._apply_after_id = self.after_idle(self._flush_apply)
        if reason:
            self._debug_log_call(f"apply_pattern_request:{reason}")

    def _flush_apply(self) -> None:
        self._apply_after_id = None
        if self._apply_in_progress:
            return
        if getattr(self, "_suspend_pattern_apply", False) or self._pattern_tree_disabled():
            return
        key = self._pending_key
        force = self._pending_force
        self._pending_key = None
        self._pending_force = False
        if key is None:
            return
        if key not in self.solution_by_key:
            return
        self._update_pattern_detail_only(key)
        if (not force) and key == self._current_applied_key:
            return
        self._apply_in_progress = True
        try:
            self._apply_solution_by_key(key)
            self._current_applied_key = key
        finally:
            self._apply_in_progress = False
        self.canvas.draw_idle()

    def on_pattern_select(self, event=None):
        if not hasattr(self, "pattern_tree") or not hasattr(
            self, "pattern_detail_var"
        ):
            return
        if self._pattern_tree_disabled():
            return

        selection = self.pattern_tree.selection()
        if not selection:
            self.pattern_detail_var.set("")
            return

        key = selection[0]
        self._update_pattern_detail_only(key)
        if getattr(self, "_suspend_pattern_apply", False):
            return
        self._request_apply(key, force=False, reason="TreeviewSelect")

    def on_pattern_click_apply(self, event):
        if getattr(self, "_suspend_pattern_apply", False):
            return
        if not hasattr(self, "pattern_tree"):
            return
        if self._pattern_tree_disabled():
            return
        row_id = self.pattern_tree.identify_row(event.y)
        if not row_id:
            return
        selection = self.pattern_tree.selection()
        if not selection or selection[0] != row_id:
            self.pattern_tree.selection_set(row_id)
        self._update_pattern_detail_only(row_id)
        self._request_apply(row_id, force=True, reason="MouseClick")

    def _update_pattern_detail_only(self, key: str) -> str:
        self._debug_log_call("on_pattern_select")
        solution = self.solution_by_key.get(key)
        if not solution:
            self.pattern_detail_var.set("")
            return ""

        metrics = solution.metrics
        display = solution.display
        stability = float(metrics.get("stability", 0.0))
        min_support = float(metrics.get("min_support", 0.0))
        edge_contact = float(metrics.get("edge_contact", 0.0))
        min_edge_clearance = float(metrics.get("min_edge_clearance", 0.0))
        risk_reasons = []
        if stability < RISK_STABILITY_THRESHOLD:
            risk_reasons.append("niska stabilność warstwy")
        if min_support < RISK_SUPPORT_THRESHOLD:
            risk_reasons.append("karton podparty w <50%")
        if edge_contact < RISK_CONTACT_THRESHOLD:
            risk_reasons.append("słaby kontakt krawędziowy")
        if min_edge_clearance < 0:
            risk_reasons.append("wystawanie poza obrys palety")
        instability_risk = bool(risk_reasons) or metrics.get("instability_risk", 0.0) > 0.5
        risk_text = (
            "Tak: " + ", ".join(risk_reasons)
            if instability_risk and risk_reasons
            else ("Tak" if instability_risk else "Nie")
        )
        wx = metrics.get("weakest_carton_x", float("nan"))
        wy = metrics.get("weakest_carton_y", float("nan"))
        weakest_support = metrics.get("weakest_support", 0.0)
        if math.isfinite(wx) and math.isfinite(wy):
            weakest_text = (
                f"najmniej podparty karton przy ({wx:.0f}, {wy:.0f}) mm "
                f"({weakest_support * 100:.1f}% podparcia)"
            )
        else:
            weakest_text = "brak kartonów w układzie"

        detail_text = (
            f"{display}: środek ciężkości {metrics.get('com_offset', 0.0):.0f} mm od centrum, "
            f"podparcie średnie {metrics.get('support_fraction', 0.0) * 100:.1f}% "
            f"(min {min_support * 100:.1f}%), "
            f"min. luz przy krawędzi {min_edge_clearance:.1f} mm, orientacje mieszane "
            f"{metrics.get('orientation_mix', 0.0) * 100:.1f}%, {weakest_text}. "
            f"Ryzyko utraty stabilności: {risk_text}."
        )
        self.pattern_detail_var.set(detail_text)
        return display

    def _apply_solution_by_key(self, key: str) -> None:
        """Update layout selection and redraw charts for the chosen pattern."""
        solution = self.solution_by_key.get(key)
        if not solution:
            return
        if hasattr(self, "odd_layout_var"):
            self.odd_layout_var.set(solution.display)
        if hasattr(self, "even_layout_var"):
            self.even_layout_var.set(solution.display)
        self.update_layers(force=True, draw=True, draw_idle=True)
        self.update_summary()

    def adjust_spacing(self, delta: float) -> None:
        """Increase or decrease carton spacing by ``delta`` millimeters."""
        try:
            current = float(self.spacing_var.get().replace(",", "."))
        except ValueError:
            current = 0.0
        new_val = max(0.0, current + delta)
        self.spacing_var.set(f"{new_val:.1f}")
        self.compute_pallet()

    # ------------------------------------------------------------------
    # JSON pattern export / import helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _slugify_filename(value: str) -> str:
        slug = re.sub(r"[^\w\-]+", "_", value.strip().lower())
        slug = slug.strip("_")
        return slug or "export"

    def _choose_pally_directory(self) -> None:
        path = filedialog.askdirectory(initialdir=self.pally_out_dir_var.get())
        if path:
            self.pally_out_dir_var.set(path)

    def export_pally_json(self) -> None:
        if not self.layers:
            messagebox.showwarning("Brak warstw", "Brak warstw do eksportu.")
            return

        name = self.pally_name_var.get().strip() or "export"
        out_dir = self.pally_out_dir_var.get().strip()
        if not out_dir:
            messagebox.showwarning("Brak folderu", "Podaj folder zapisu.")
            return

        pallet_w = int(round(parse_dim(self.pallet_w_var)))
        pallet_l = int(round(parse_dim(self.pallet_l_var)))
        pallet_h = int(round(parse_dim(self.pallet_h_var)))
        box_w = int(round(parse_dim(self.box_w_var)))
        box_l = int(round(parse_dim(self.box_l_var)))
        box_h = int(round(parse_dim(self.box_h_var)))

        if min(pallet_w, pallet_l, pallet_h, box_w, box_l, box_h) <= 0:
            messagebox.showwarning(
                "Brak danych", "Podaj poprawne wymiary palety i kartonu."
            )
            return

        try:
            overhang_ends = int(parse_float(self.pally_overhang_ends_var.get()))
            overhang_sides = int(parse_float(self.pally_overhang_sides_var.get()))
        except Exception:
            messagebox.showwarning("Błąd", "Niepoprawne wartości overhangu.")
            return

        weight_text = self.manual_carton_weight_var.get().strip()
        if weight_text:
            try:
                weight_kg = parse_float(weight_text)
            except Exception:
                messagebox.showwarning("Błąd", "Niepoprawna masa kartonu.")
                return
        else:
            weight_kg = self.carton_weights.get(self.carton_var.get(), 0)

        if not weight_kg:
            messagebox.showwarning(
                "Brak masy",
                "Brak masy kartonu. Uzupełnij pole lub wybierz karton z wagą.",
            )
            return

        box_weight_g = int(round(weight_kg * 1000))
        layer_rects_list = []
        for idx, layer in enumerate(self.layers):
            if idx >= len(self.transformations):
                messagebox.showwarning(
                    "Brak transformacji",
                    "Nie można pobrać transformacji dla wszystkich warstw.",
                )
                return
            coords = self.apply_transformation(
                list(layer),
                self.transformations[idx],
                pallet_w,
                pallet_l,
            )
            layer_rects_list.append(coords)

        slips_after = parse_slips_after(
            self.pally_slips_after_var.get(), len(layer_rects_list)
        )
        config = PallyExportConfig(
            name=name,
            pallet_w=pallet_w,
            pallet_l=pallet_l,
            pallet_h=pallet_h,
            box_w=box_w,
            box_l=box_l,
            box_h=box_h,
            box_weight_g=box_weight_g,
            overhang_ends=overhang_ends,
            overhang_sides=overhang_sides,
            label_orientation=int(self.pally_label_orientation_var.get()),
            swap_axes_for_pally=bool(self.pally_swap_axes_var.get()),
        )

        payload = build_pally_json(
            config=config, layer_rects_list=layer_rects_list, slips_after=slips_after
        )

        warnings = find_out_of_bounds(payload)
        if warnings:
            messagebox.showwarning(
                "Poza paletą", "\n".join(warnings), parent=self.winfo_toplevel()
            )

        os.makedirs(out_dir, exist_ok=True)
        filename = f"{self._slugify_filename(name)}.json"
        path = os.path.join(out_dir, filename)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=4, ensure_ascii=False)
        if hasattr(self, "status_var"):
            self.status_var.set(f"Zapisano PALLY JSON: {path}")
        self.pally_result_path_var.set(f"Plik wynikowy: {path}")

    def gather_pattern_data(self, name: str = "") -> dict:
        """Collect current pallet layout as a JSON-serialisable dict."""
        return gather_pattern_data_core(self, name=name, parse_dim=parse_dim)

    def apply_pattern_data(self, data: dict) -> None:
        """Load pallet layout from a dictionary."""
        apply_pattern_data_core(self, data)

    def _modifier_active(self, event, mask: int) -> bool:
        gui_event = getattr(event, "guiEvent", None)
        if gui_event is not None and hasattr(gui_event, "state"):
            try:
                return bool(gui_event.state & mask)
            except Exception:
                pass
        key = (event.key or "").lower()
        if mask == 0x0001:
            return "shift" in key
        if mask == 0x0004:
            return "ctrl" in key or "control" in key or "cmd" in key
        return False

    def _shift_active(self, event) -> bool:
        return self._modifier_active(event, 0x0001)

    def _ctrl_active(self, event) -> bool:
        return self._modifier_active(event, 0x0004)

    @staticmethod
    def _record_state(obj) -> None:
        recorder = getattr(obj, "push_undo_state", None)
        if recorder is not None:
            recorder()

    def push_undo_state(self) -> None:
        state = {
            "layers": [list(layer) for layer in self.layers],
            "carton_ids": [list(ids) for ids in self.carton_ids],
            "selected": set(self.selected_indices),
        }
        if self.undo_stack:
            last = self.undo_stack[-1]
            if last["layers"] == state["layers"] and last["carton_ids"] == state["carton_ids"]:
                return
        self.undo_stack.append(state)
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)

    def undo(self) -> None:
        if not self.undo_stack:
            return
        state = self.undo_stack.pop()
        self.layers = [list(layer) for layer in state["layers"]]
        self.carton_ids = [list(ids) for ids in state["carton_ids"]]
        self._set_selection_pairs(state.get("selected", set()))
        self.drag_info = None
        self.drag_select_origin = None
        self.drag_snapshot_saved = False
        self.draw_pallet()
        self.update_summary()
        self.highlight_selection()

    def on_key_press(self, event):
        if not self.modify_mode_var.get():
            return
        key = (event.key or "").lower()
        if key in {"ctrl+z", "control+z", "cmd+z"} or (
            key == "z" and self._ctrl_active(event)
        ):
            self.undo()

    def save_pattern_dialog(self):
        name = simpledialog.askstring("Zapisz wzór", "Nazwa wzoru:")
        if not name:
            return
        data = self.gather_pattern_data(name)
        try:
            save_pattern(name, data)
            path = os.path.join(get_pattern_dir(), f"{name}.json")
            messagebox.showinfo("Sukces", f"Zapisano wzór '{name}' w {path}")
        except Exception as exc:
            messagebox.showerror("Błąd zapisu", str(exc))

    def load_pattern_dialog(self):
        ensure_pattern_dir()
        path = filedialog.askopenfilename(
            title="Wczytaj wzór",
            initialdir=get_pattern_dir(),
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            messagebox.showerror("Błąd", str(exc))
            return
        self.apply_pattern_data(data)
