import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import matplotlib
import json

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk,
)
from packing_app.core import save_pattern, algorithms
from packing_app.core.pattern_io import (
    pattern_path,
    _ensure_dir,
    PATTERN_DIR,
)
from palletizer_core import (
    Carton,
    Pallet,
    PatternSelector,
    EvenOddSequencer,
)
from core.utils import (
    load_cartons,
    load_pallets,
    load_cartons_with_weights,
    load_pallets_with_weights,
    load_materials,
    load_slip_sheets,
)


def parse_dim(var: tk.StringVar) -> float:
    try:
        val = float(var.get().replace(",", "."))
        return max(0, val)
    except Exception:
        messagebox.showwarning("Błąd", "Wprowadzono niepoprawną wartość. Użyto 0.")
        return 0.0


def apply_spacing(pattern, spacing):
    """Center boxes within spaced slots."""
    adjusted = []
    for x, y, w, h in pattern:
        new_w = w - spacing
        new_h = h - spacing
        adjusted.append((x + spacing / 2, y + spacing / 2, new_w, new_h))
    return adjusted


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
        self.pack(fill=tk.BOTH, expand=True)
        self.layouts = []
        self.layers = []
        self.carton_ids = []
        self.layer_patterns = []
        self.transformations = []
        self.products_per_carton = 1
        self.tape_per_carton = 0.0
        self.film_per_pallet = 0.0
        self.best_layout_name = ""
        self.best_even = []
        self.best_odd = []
        self.modify_mode_var = tk.BooleanVar(value=False)
        self.patches = []
        self.selected_indices = set()
        self.drag_offset = (0, 0)
        self.drag_info = None
        self.drag_select_origin = None
        self.press_cid = None
        self.motion_cid = None
        self.release_cid = None
        self.context_menu = None
        self.context_layer = 0
        self.context_pos = (0, 0)
        self.wolny_solutions = []
        self.wolny_index = 0
        self.wolny_get_next = None
        self.build_ui()

    def layers_linked(self) -> bool:
        """Return True if odd and even layers use the same layout algorithm."""
        try:
            return self.odd_layout_var.get() == self.even_layout_var.get()
        except Exception:
            return False

    def build_ui(self):
        pallet_frame = ttk.LabelFrame(self, text="Parametry palety")
        pallet_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(pallet_frame, text="Paleta:").grid(row=0, column=0, padx=5, pady=5)
        self.pallet_var = tk.StringVar(value=self.predefined_pallets[0]["name"])
        pallet_menu = ttk.OptionMenu(
            pallet_frame,
            self.pallet_var,
            self.predefined_pallets[0]["name"],
            *[p["name"] for p in self.predefined_pallets],
            command=self.on_pallet_selected,
        )
        pallet_menu.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(pallet_frame, text="W (mm):").grid(row=0, column=2, padx=5, pady=5)
        self.pallet_w_var = tk.StringVar(value=str(self.predefined_pallets[0]["w"]))
        entry_pallet_w = ttk.Entry(
            pallet_frame, textvariable=self.pallet_w_var, width=10
        )
        entry_pallet_w.grid(row=0, column=3, padx=5, pady=5)
        entry_pallet_w.bind("<Return>", self.compute_pallet)

        ttk.Label(pallet_frame, text="L (mm):").grid(row=0, column=4, padx=5, pady=5)
        self.pallet_l_var = tk.StringVar(value=str(self.predefined_pallets[0]["l"]))
        entry_pallet_l = ttk.Entry(
            pallet_frame, textvariable=self.pallet_l_var, width=10
        )
        entry_pallet_l.grid(row=0, column=5, padx=5, pady=5)
        entry_pallet_l.bind("<Return>", self.compute_pallet)

        ttk.Label(pallet_frame, text="H (mm):").grid(row=0, column=6, padx=5, pady=5)
        self.pallet_h_var = tk.StringVar(value=str(self.predefined_pallets[0]["h"]))
        entry_pallet_h = ttk.Entry(
            pallet_frame, textvariable=self.pallet_h_var, width=10
        )
        entry_pallet_h.grid(row=0, column=7, padx=5, pady=5)
        entry_pallet_h.bind("<Return>", self.compute_pallet)

        carton_frame = ttk.LabelFrame(self, text="Parametry kartonu")
        carton_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(carton_frame, text="Karton:").grid(row=0, column=0, padx=5, pady=5)
        self.carton_var = tk.StringVar(value=list(self.predefined_cartons.keys())[0])
        carton_menu = ttk.OptionMenu(
            carton_frame,
            self.carton_var,
            list(self.predefined_cartons.keys())[0],
            *self.predefined_cartons.keys(),
            command=self.on_carton_selected,
        )
        carton_menu.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(carton_frame, text="W (mm):").grid(row=0, column=2, padx=5, pady=5)
        self.box_w_var = tk.StringVar(
            value=str(
                self.predefined_cartons[list(self.predefined_cartons.keys())[0]][0]
            )
        )
        entry_box_w = ttk.Entry(carton_frame, textvariable=self.box_w_var, width=10)
        entry_box_w.grid(row=0, column=3, padx=5, pady=5)
        entry_box_w.bind("<Return>", self.compute_pallet)

        ttk.Label(carton_frame, text="L (mm):").grid(row=0, column=4, padx=5, pady=5)
        self.box_l_var = tk.StringVar(
            value=str(
                self.predefined_cartons[list(self.predefined_cartons.keys())[0]][1]
            )
        )
        entry_box_l = ttk.Entry(carton_frame, textvariable=self.box_l_var, width=10)
        entry_box_l.grid(row=0, column=5, padx=5, pady=5)
        entry_box_l.bind("<Return>", self.compute_pallet)

        ttk.Label(carton_frame, text="H (mm):").grid(row=0, column=6, padx=5, pady=5)
        self.box_h_var = tk.StringVar(
            value=str(
                self.predefined_cartons[list(self.predefined_cartons.keys())[0]][2]
            )
        )
        entry_box_h = ttk.Entry(carton_frame, textvariable=self.box_h_var, width=10)
        entry_box_h.grid(row=0, column=7, padx=5, pady=5)
        entry_box_h.bind("<Return>", self.compute_pallet)

        ttk.Label(carton_frame, text="Grubość tektury (mm):").grid(
            row=1, column=0, padx=5, pady=5
        )
        self.cardboard_thickness_var = tk.StringVar(value="3")
        entry_cardboard = ttk.Entry(
            carton_frame,
            textvariable=self.cardboard_thickness_var,
            width=10,
            validate="key",
            validatecommand=(self.register(self.validate_number), "%P"),
        )
        entry_cardboard.grid(row=1, column=1, padx=5, pady=5)
        entry_cardboard.bind("<Return>", self.compute_pallet)

        ttk.Label(carton_frame, text="Wymiary zewnętrzne (mm):").grid(
            row=1, column=2, padx=5, pady=5
        )
        self.ext_dims_label = ttk.Label(carton_frame, text="")
        self.ext_dims_label.grid(
            row=1, column=3, columnspan=5, padx=5, pady=5, sticky="w"
        )
        self.cardboard_thickness_var.trace_add("write", self.update_external_dimensions)
        self.box_w_var.trace_add("write", self.update_external_dimensions)
        self.box_l_var.trace_add("write", self.update_external_dimensions)
        self.box_h_var.trace_add("write", self.update_external_dimensions)
        self.update_external_dimensions()

        ttk.Label(carton_frame, text="Odstęp między kartonami (mm):").grid(
            row=2, column=0, padx=5, pady=5
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
        ).pack(side=tk.LEFT)
        ttk.Button(
            spacing_frame, text="-", width=2, command=lambda: self.adjust_spacing(-1)
        ).pack(side=tk.LEFT)
        spacing_frame.grid(row=2, column=1, padx=5, pady=5)
        entry_spacing.bind("<Return>", self.compute_pallet)

        layers_frame = ttk.LabelFrame(self, text="Ustawienia warstw")
        layers_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(layers_frame, text="Liczba warstw:").grid(
            row=0, column=0, padx=5, pady=5
        )
        self.num_layers_var = tk.StringVar(value="1")
        entry_num_layers = ttk.Entry(
            layers_frame, textvariable=self.num_layers_var, width=5
        )
        entry_num_layers.grid(row=0, column=1, padx=5, pady=5)
        entry_num_layers.bind("<Return>", self.compute_pallet)

        ttk.Label(layers_frame, text="Maksymalna wysokość ułożenia (mm):").grid(
            row=1, column=0, padx=5, pady=5
        )
        # Default maximum stack height is 1600 mm which roughly corresponds to
        # a common limit for palletized loads. Set to 0 to disable the limit.
        self.max_stack_var = tk.StringVar(value="1600")
        entry_max_stack = ttk.Entry(
            layers_frame, textvariable=self.max_stack_var, width=8
        )
        entry_max_stack.grid(row=1, column=1, padx=5, pady=5)
        entry_max_stack.bind("<Return>", self.compute_pallet)
        self.include_pallet_height_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            layers_frame,
            text="Uwzględnij wysokość nośnika",
            variable=self.include_pallet_height_var,
            command=self.compute_pallet,
        ).grid(row=1, column=2, columnspan=2, padx=5, pady=5, sticky="w")

        self.shift_even_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            layers_frame,
            text="Przesuwaj warstwy parzyste",
            variable=self.shift_even_var,
            command=self.compute_pallet,
        ).grid(row=1, column=4, columnspan=2, padx=5, pady=5, sticky="w")

        ttk.Label(layers_frame, text="Centrowanie:").grid(
            row=0, column=2, padx=5, pady=5
        )
        self.center_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            layers_frame, variable=self.center_var, command=self.compute_pallet
        ).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(layers_frame, text="Tryb:").grid(row=0, column=4, padx=5, pady=5)
        self.center_mode_var = tk.StringVar(value="Cała warstwa")
        ttk.OptionMenu(
            layers_frame,
            self.center_mode_var,
            "Cała warstwa",
            "Cała warstwa",
            "Poszczególne obszary",
            command=self.compute_pallet,
        ).grid(row=0, column=5, padx=5, pady=5)

        self.maximize_mixed = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            layers_frame,
            text="Maksymalizuj mixed",
            variable=self.maximize_mixed,
            command=self.compute_pallet,
        ).grid(row=0, column=6, padx=5, pady=5, sticky="w")

        ttk.Label(layers_frame, text="Liczba przekładek:").grid(
            row=2, column=0, padx=5, pady=5
        )
        self.slip_count_var = tk.StringVar(value="0")
        entry_slip_count = ttk.Entry(
            layers_frame,
            textvariable=self.slip_count_var,
            width=5,
            validate="key",
            validatecommand=(self.register(self.validate_number), "%P"),
        )
        entry_slip_count.grid(row=2, column=1, padx=5, pady=5)
        entry_slip_count.bind("<Return>", self.compute_pallet)

        self.transform_frame = ttk.Frame(layers_frame)
        # Move transform options to the right to save vertical space
        self.transform_frame.grid(
            row=0, column=7, rowspan=3, padx=5, pady=5, sticky="n"
        )

        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=tk.X, padx=10, pady=5)

        control_frame = ttk.Frame(bottom_frame)
        control_frame.pack(side=tk.LEFT, padx=5)

        self.compute_btn = ttk.Button(
            control_frame, text="Oblicz", command=self.compute_pallet
        )
        self.compute_btn.pack(side=tk.LEFT, padx=5)
        self.prev_btn = ttk.Button(
            control_frame, text="Poprzedni", command=self.prev_wolny
        )
        self.prev_btn.pack(side=tk.LEFT, padx=5)
        self.prev_btn.state(["disabled"])
        self.next_btn = ttk.Button(
            control_frame, text="Następny", command=self.next_wolny
        )
        self.next_btn.pack(side=tk.LEFT, padx=5)
        self.next_btn.state(["disabled"])
        ttk.Checkbutton(
            control_frame,
            text="Tryb edycji",
            variable=self.modify_mode_var,
            command=self.toggle_edit_mode,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            control_frame,
            text="Wstaw karton",
            command=self.insert_carton_button,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            control_frame,
            text="Usu\u0144 karton",
            command=self.delete_selected_carton,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            control_frame,
            text="Zapisz wzór",
            command=self.save_pattern_dialog,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            control_frame,
            text="Wczytaj wzór",
            command=self.load_pattern_dialog,
        ).pack(side=tk.LEFT, padx=5)
        self.status_var = tk.StringVar(value="")
        self.status_label = ttk.Label(control_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT, padx=5)

        self.summary_frame = ttk.LabelFrame(bottom_frame, text="Obliczenia")
        self.summary_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.totals_label = ttk.Label(self.summary_frame, text="")
        self.totals_label.pack(side=tk.LEFT, padx=5)
        self.materials_label = ttk.Label(self.summary_frame, text="")
        self.materials_label.pack(side=tk.LEFT, padx=5)
        self.weight_label = ttk.Label(self.summary_frame, text="")
        self.weight_label.pack(side=tk.LEFT, padx=5)
        self.area_label = ttk.Label(self.summary_frame, text="")
        self.area_label.pack(side=tk.LEFT, padx=5)

        self.fig = plt.Figure(figsize=(12, 6))
        self.ax_odd = self.fig.add_subplot(131)
        self.ax_even = self.fig.add_subplot(132)
        self.ax_overlay = self.fig.add_subplot(133)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.pack()
        self.canvas.draw()

        self.compute_pallet()

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

    def update_transform_frame(self):
        for widget in self.transform_frame.winfo_children():
            widget.destroy()
        layout_options = [layout[2] for layout in self.layouts]
        transform_options = [
            "Brak",
            "Odbicie wzdłuż dłuższego boku",
            "Odbicie wzdłuż krótszego boku",
            "Obrót 180°",
        ]

        prev_odd_layout = getattr(self, "odd_layout_var", None)
        prev_even_layout = getattr(self, "even_layout_var", None)
        prev_odd_transform = getattr(self, "odd_transform_var", None)
        prev_even_transform = getattr(self, "even_transform_var", None)

        interlock_name = "Interlock"
        if interlock_name in layout_options:
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
        ttk.OptionMenu(
            self.transform_frame,
            self.odd_layout_var,
            odd_default,
            *layout_options,
            command=lambda *_: self.update_layers("odd"),
        ).grid(row=0, column=1, padx=5, pady=2)
        self.odd_transform_var = tk.StringVar(value=odd_tr_default)
        ttk.OptionMenu(
            self.transform_frame,
            self.odd_transform_var,
            odd_tr_default,
            *transform_options,
            command=lambda *_: self.update_layers("odd"),
        ).grid(row=0, column=2, padx=5, pady=2)

        ttk.Label(self.transform_frame, text="Warstwy parzyste:").grid(
            row=1, column=0, padx=5, pady=2
        )
        self.even_layout_var = tk.StringVar(value=even_default)
        ttk.OptionMenu(
            self.transform_frame,
            self.even_layout_var,
            even_default,
            *layout_options,
            command=lambda *_: self.update_layers("even"),
        ).grid(row=1, column=1, padx=5, pady=2)
        self.even_transform_var = tk.StringVar(value=even_tr_default)
        ttk.OptionMenu(
            self.transform_frame,
            self.even_transform_var,
            even_tr_default,
            *transform_options,
            command=lambda *_: self.update_layers("even"),
        ).grid(row=1, column=2, padx=5, pady=2)

    def update_layers(self, side="both", force=False, *args):
        num_layers = getattr(self, "num_layers", int(parse_dim(self.num_layers_var)))
        if side == "both" or not self.layers:
            self.layers = [list() for _ in range(num_layers)]
            self.carton_ids = [list() for _ in range(num_layers)]
            self.layer_patterns = ["" for _ in range(num_layers)]
            self.transformations = ["" for _ in range(num_layers)]
        self.selected_indices.clear()
        self.drag_info = None
        odd_name = self.odd_layout_var.get()
        even_name = self.even_layout_var.get()
        odd_idx = self.layout_map.get(odd_name, 0)
        even_idx = self.layout_map.get(even_name, 0)
        odd_source = (
            self.best_odd
            if odd_name == self.best_layout_name
            else self.layouts[odd_idx][1]
        )
        even_source = (
            self.best_even
            if even_name == self.best_layout_name
            else self.layouts[even_idx][1]
        )
        for i in range(1, num_layers + 1):
            idx = i - 1
            if i % 2 == 1:
                if side in ("both", "odd"):
                    if idx >= len(self.layers):
                        self.layers.append(list(odd_source))
                        self.carton_ids.append(list(range(1, len(odd_source) + 1)))
                    elif self.layer_patterns[idx] != odd_name or force:
                        self.layers[idx] = list(odd_source)
                        self.carton_ids[idx] = list(range(1, len(odd_source) + 1))
                    self.layer_patterns[idx] = odd_name
                    self.transformations[idx] = self.odd_transform_var.get()
            else:
                if side in ("both", "even"):
                    if idx >= len(self.layers):
                        self.layers.append(list(even_source))
                        self.carton_ids.append(list(range(1, len(even_source) + 1)))
                    elif self.layer_patterns[idx] != even_name or force:
                        self.layers[idx] = list(even_source)
                        self.carton_ids[idx] = list(range(1, len(even_source) + 1))
                    self.layer_patterns[idx] = even_name
                    self.transformations[idx] = self.even_transform_var.get()
        self.renumber_layers()
        self.draw_pallet()

    def on_pallet_selected(self, *args):
        selected_pallet = next(
            p for p in self.predefined_pallets if p["name"] == self.pallet_var.get()
        )
        self.pallet_w_var.set(str(selected_pallet["w"]))
        self.pallet_l_var.set(str(selected_pallet["l"]))
        self.pallet_h_var.set(str(selected_pallet["h"]))
        self.compute_pallet()

    def on_carton_selected(self, *args):
        dims = self.predefined_cartons[self.carton_var.get()]
        self.box_w_var.set(str(dims[0]))
        self.box_l_var.set(str(dims[1]))
        self.box_h_var.set(str(dims[2]))
        self.compute_pallet()

    @staticmethod
    def apply_transformation(positions, transform, pallet_w, pallet_l):
        new_positions = []
        for x, y, w, h in positions:
            if transform == "Brak":
                new_positions.append((x, y, w, h))
            elif transform == "Odbicie wzdłuż dłuższego boku":
                if pallet_w >= pallet_l:
                    new_x = pallet_w - x - w
                    new_y = y
                else:
                    new_x = x
                    new_y = pallet_l - y - h
                new_positions.append((new_x, new_y, w, h))
            elif transform == "Odbicie wzdłuż krótszego boku":
                if pallet_w < pallet_l:
                    new_x = pallet_w - x - w
                    new_y = y
                else:
                    new_x = x
                    new_y = pallet_l - y - h
                new_positions.append((new_x, new_y, w, h))
            elif transform == "Obrót 180°":
                new_x = pallet_w - x - w
                new_y = pallet_l - y - h
                new_positions.append((new_x, new_y, w, h))
        return new_positions

    @staticmethod
    def inverse_transformation(positions, transform, pallet_w, pallet_l):
        """Reverse the transformation applied to the positions."""
        new_positions = []
        for x, y, w, h in positions:
            new_positions.extend(
                TabPallet.apply_transformation(
                    [(x, y, w, h)],
                    transform,
                    pallet_w,
                    pallet_l,
                )
            )
        return new_positions

    def group_cartons(self, positions):
        """Group cartons that touch or overlap using AABB collision detection."""

        def collide(a, b):
            ax, ay, aw, ah = a
            bx, by, bw, bh = b
            return not (
                ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay
            )

        groups = []
        used = set()
        for i in range(len(positions)):
            if i in used:
                continue
            stack = [i]
            used.add(i)
            current_group = []
            while stack:
                idx = stack.pop()
                current_group.append(positions[idx])
                for j in range(len(positions)):
                    if j in used:
                        continue
                    if collide(positions[idx], positions[j]):
                        used.add(j)
                        stack.append(j)
            groups.append(current_group)
        return groups

    def detect_collisions(self, positions, pallet_w, pallet_l):
        """Return indices of cartons that overlap or lie outside the pallet."""

        index_map = {id(pos): idx for idx, pos in enumerate(positions)}
        collisions = set()

        for group in self.group_cartons(positions):
            if len(group) > 1:
                for pos in group:
                    collisions.add(index_map[id(pos)])

        for idx, (x, y, w, h) in enumerate(positions):
            if x < 0 or y < 0 or x + w > pallet_w or y + h > pallet_l:
                collisions.add(idx)

        return collisions

    def center_layout(self, positions, pallet_w, pallet_l):
        if not positions or not self.center_var.get():
            return positions
        if self.center_mode_var.get() == "Cała warstwa":
            x_min = min(x for x, y, w, h in positions)
            x_max = max(x + w for x, y, w, h in positions)
            y_min = min(y for x, y, w, h in positions)
            y_max = max(y + h for x, y, w, h in positions)
            offset_x = (pallet_w - (x_max - x_min)) / 2 - x_min
            offset_y = (pallet_l - (y_max - y_min)) / 2 - y_min
            return [(x + offset_x, y + offset_y, w, h) for x, y, w, h in positions]
        else:
            groups = self.group_cartons(positions)
            centered_positions = []
            for group in groups:
                x_min = min(x for x, y, w, h in group)
                x_max = max(x + w for x, y, w, h in group)
                y_min = min(y for x, y, w, h in group)
                y_max = max(y + h for x, y, w, h in group)
                offset_x = (pallet_w - (x_max - x_min)) / 2 - x_min
                offset_y = (pallet_l - (y_max - y_min)) / 2 - y_min
                centered_positions.extend(
                    [(x + offset_x, y + offset_y, w, h) for x, y, w, h in group]
                )

            # If centering individual groups makes them collide, fall back to
            # centering the entire layer instead of merging the groups.
            if len(self.group_cartons(centered_positions)) != len(groups):
                x_min = min(x for x, y, w, h in positions)
                x_max = max(x + w for x, y, w, h in positions)
                y_min = min(y for x, y, w, h in positions)
                y_max = max(y + h for x, y, w, h in positions)
                offset_x = (pallet_w - (x_max - x_min)) / 2 - x_min
                offset_y = (pallet_l - (y_max - y_min)) / 2 - y_min
                return [(x + offset_x, y + offset_y, w, h) for x, y, w, h in positions]
            return centered_positions

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

    def _get_default_layout(
        self,
        selector: PatternSelector,
        carton: Carton,
        pallet: Pallet,
        pallet_w: float,
        pallet_l: float,
    ) -> tuple[dict, str, list, list]:
        """Return available patterns and best even/odd layers.

        The interlock layout is preferred when available. The returned display
        name always matches the pattern used for sequencing.
        """

        patterns = selector.generate_all(maximize_mixed=self.maximize_mixed.get())
        if "interlock" in patterns:
            best_name = "Interlock"
            best_pattern = patterns["interlock"]
        else:
            raw_name, best_pattern, _ = selector.best(
                maximize_mixed=self.maximize_mixed.get()
            )
            best_name = raw_name.replace("_", " ").capitalize()

        seq = EvenOddSequencer(best_pattern, carton, pallet)
        even_base, odd_shifted = seq.best_shift()
        if self.shift_even_var.get():
            best_even = self.center_layout(odd_shifted, pallet_w, pallet_l)
            best_odd = self.center_layout(even_base, pallet_w, pallet_l)
        else:
            best_even = self.center_layout(even_base, pallet_w, pallet_l)
            best_odd = self.center_layout(odd_shifted, pallet_w, pallet_l)

        return patterns, best_name, best_even, best_odd

    def compute_pallet(self, event=None):
        """Calculate carton layouts on the pallet.

        The interlock pattern is always selected as the default layout. Other
        patterns are still generated for manual selection.
        """
        self.selected_indices.clear()
        self.drag_info = None
        if hasattr(self, "status_var"):
            self.status_var.set("Obliczanie...")
            self.status_label.update_idletasks()
        if hasattr(self, "compute_btn"):
            self.compute_btn.state(["disabled"])

        try:
            pallet_w = parse_dim(self.pallet_w_var)
            pallet_l = parse_dim(self.pallet_l_var)
            pallet_h = parse_dim(self.pallet_h_var)
            box_w = parse_dim(self.box_w_var)
            box_l = parse_dim(self.box_l_var)
            box_h = parse_dim(self.box_h_var)
            thickness = parse_dim(self.cardboard_thickness_var)
            spacing = parse_dim(self.spacing_var)
            slip_count = int(parse_dim(self.slip_count_var))
            box_w_ext = box_w + 2 * thickness
            box_l_ext = box_l + 2 * thickness
            num_layers = int(parse_dim(self.num_layers_var))
            max_stack = parse_dim(self.max_stack_var)

            if max_stack > 0:
                avail = max_stack - (
                    pallet_h if self.include_pallet_height_var.get() else 0
                )
                box_h_ext = box_h + 2 * thickness
                layer_height = box_h_ext
                if layer_height > 0:
                    num_layers = max(int(avail // layer_height), 0)
                    self.num_layers_var.set(str(num_layers))

            if (
                pallet_w == 0
                or pallet_l == 0
                or pallet_h == 0
                or box_w == 0
                or box_l == 0
                or box_h == 0
                or num_layers <= 0
            ):
                messagebox.showwarning(
                    "Błąd", "Wszystkie wymiary i liczba warstw muszą być większe od 0."
                )
                return

            self.layouts = []
            self.wolny_solutions = []
            self.wolny_index = 0
            self.wolny_get_next = None

            pallet = Pallet(pallet_w, pallet_l, pallet_h)
            calc_carton = Carton(box_w_ext + spacing, box_l_ext + spacing, box_h)
            selector = PatternSelector(calc_carton, pallet)

            (
                patterns,
                best_name,
                self.best_even,
                self.best_odd,
            ) = self._get_default_layout(
                selector,
                calc_carton,
                pallet,
                pallet_w,
                pallet_l,
            )

            wolny_res = algorithms.enumerate_packings_wolny(
                pallet_w,
                pallet_l,
                box_w_ext + spacing,
                box_l_ext + spacing,
                want=15,
                time_first=5,
                time_each=3,
                seed=0,
            )
            if wolny_res:
                self.wolny_solutions, self.wolny_get_next = (
                    wolny_res if isinstance(wolny_res, tuple) else (wolny_res, None)
                )
                patterns["wolny"] = self.wolny_solutions[0]
            else:
                patterns["wolny"] = []

            def adjust(patt):
                return apply_spacing(patt, spacing)

            patterns = {k: adjust(v) for k, v in patterns.items()}
            self.best_even = adjust(self.best_even)
            self.best_odd = adjust(self.best_odd)

            for name, patt in patterns.items():
                centered = self.center_layout(patt, pallet_w, pallet_l)
                display = name.replace("_", " ").capitalize()
                self.layouts.append((len(centered), centered, display))

            self.best_layout_name = best_name
            # Force the interlock pattern to be the default selection when
            # available.  Fallback to the best scored pattern otherwise.
            if "interlock" in patterns:
                best_name = "interlock"
                best_pattern = selector.generate_all()["interlock"]
            else:
                raw_name, best_pattern, _ = selector.best(
                    maximize_mixed=self.maximize_mixed.get()
                )
                best_name = raw_name

            seq = EvenOddSequencer(best_pattern, calc_carton, pallet)
            even_base, odd_shifted = seq.best_shift()
            if self.shift_even_var.get():
                self.best_even = adjust(
                    self.center_layout(odd_shifted, pallet_w, pallet_l)
                )
                self.best_odd = adjust(
                    self.center_layout(even_base, pallet_w, pallet_l)
                )
            else:
                self.best_even = adjust(
                    self.center_layout(even_base, pallet_w, pallet_l)
                )
                self.best_odd = adjust(
                    self.center_layout(odd_shifted, pallet_w, pallet_l)
                )
            self.best_layout_name = best_name.replace("_", " ").capitalize()

            self.layout_map = {
                name: idx for idx, (_, __, name) in enumerate(self.layouts)
            }
            if self.wolny_solutions:
                self.prev_btn.state(["!disabled"])
                self.next_btn.state(["!disabled"])
            else:
                self.prev_btn.state(["disabled"])
                self.next_btn.state(["disabled"])
            self.update_transform_frame()
            self.num_layers = num_layers
            self.slip_count = slip_count
            self.update_layers()
            getattr(self, "sort_layers", lambda: None)()
            self.update_summary()
        finally:
            if hasattr(self, "status_var"):
                self.status_var.set("")
            if hasattr(self, "compute_btn"):
                self.compute_btn.state(["!disabled"])

    def draw_pallet(self):
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
                    ax.text(
                        x + w / 2,
                        y + h / 2,
                        str(self.carton_ids[idx][i] if idx < len(self.carton_ids) and i < len(self.carton_ids[idx]) else i + 1),
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
        for layer_idx, layer in enumerate(self.layers):
            order = sorted(range(len(layer)), key=lambda i: (layer[i][1], layer[i][0]))
            if order != list(range(len(layer))):
                self.layers[layer_idx] = [layer[i] for i in order]
                self.carton_ids[layer_idx] = [self.carton_ids[layer_idx][i] for i in order]
                mapping = {old_idx: new_idx for new_idx, old_idx in enumerate(order)}
            else:
                mapping = {i: i for i in range(len(layer))}
            for l_idx, idx in self.selected_indices:
                if l_idx == layer_idx:
                    new_sel.add((l_idx, mapping.get(idx, idx)))
                else:
                    new_sel.add((l_idx, idx))
        self.selected_indices = new_sel

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
        else:
            for cid in [self.press_cid, self.motion_cid, self.release_cid]:
                if cid is not None:
                    self.canvas.mpl_disconnect(cid)
            self.press_cid = self.motion_cid = self.release_cid = None
            self.selected_indices.clear()
            self.drag_info = None
            self.drag_select_origin = None
            self.draw_pallet()
            if hasattr(self, "status_var"):
                self.status_var.set("")

    def on_press(self, event):
        if not self.modify_mode_var.get() or event.inaxes not in [
            self.ax_odd,
            self.ax_even,
        ]:
            return
        if event.button == 3:
            self.on_right_click(event)
            return
        layer_idx = 0 if event.inaxes is self.ax_odd else 1
        if event.xdata is not None and event.ydata is not None:
            self.context_layer = layer_idx
            self.context_pos = (event.xdata, event.ydata)
        for patch, idx in self.patches[layer_idx]:
            contains, _ = patch.contains(event)
            if contains:
                if event.key == "shift":
                    if (layer_idx, idx) in self.selected_indices:
                        self.selected_indices.remove((layer_idx, idx))
                    else:
                        self.selected_indices.add((layer_idx, idx))
                    self.drag_info = None
                else:
                    if (layer_idx, idx) not in self.selected_indices:
                        self.selected_indices = {(layer_idx, idx)}
                    drag_items = []
                    for l_idx, i_idx in self.selected_indices:
                        for p, j in self.patches[l_idx]:
                            if j == i_idx:
                                x, y = p.get_xy()
                                drag_items.append(
                                    (l_idx, i_idx, p, x - event.xdata, y - event.ydata)
                                )
                                break
                    self.drag_info = drag_items
                break
        else:
            if event.key == "shift":
                self.selected_indices.clear()
                self.drag_select_origin = (event.xdata, event.ydata)
        self.highlight_selection()

    def on_motion(self, event):
        if not self.drag_info or event.xdata is None or event.ydata is None:
            return

        pallet_w = parse_dim(self.pallet_w_var)
        pallet_l = parse_dim(self.pallet_l_var)

        for layer_idx, idx, patch, dx, dy in self.drag_info:
            new_x = event.xdata + dx
            new_y = event.ydata + dy
            patch.set_xy((new_x, new_y))
            x, y, w, h = self.layers[layer_idx][idx]
            orig_x, orig_y, _, _ = self.inverse_transformation(
                [(new_x, new_y, w, h)],
                self.transformations[layer_idx],
                pallet_w,
                pallet_l,
            )[0]
            self.layers[layer_idx][idx] = (orig_x, orig_y, w, h)
            if self.layers_linked():
                other_layer = 1 - layer_idx
                if (
                    other_layer < len(self.layers)
                    and idx < len(self.layers[other_layer])
                    and self.layer_patterns[other_layer] == self.layer_patterns[layer_idx]
                ):
                    self.layers[other_layer][idx] = (orig_x, orig_y, w, h)
                    for p, j in self.patches[other_layer]:
                        if j == idx:
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

        layers_to_check = {item[0] for item in self.drag_info}
        if self.layers_linked():
            layers_to_check |= {1 - idx for idx in layers_to_check if 1 - idx < len(self.layers)}
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

        self.canvas.draw_idle()

    def on_release(self, event):
        if not self.drag_info:
            return

        pallet_w = parse_dim(self.pallet_w_var)
        pallet_l = parse_dim(self.pallet_l_var)

        items = self.drag_info if isinstance(self.drag_info, list) else [self.drag_info]

        for layer_idx, idx, patch, *_ in items:
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
                if j != idx or (layer_idx, j) not in self.selected_indices
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

        self.drag_info = None
        getattr(self, "sort_layers", lambda: None)()
        self.draw_pallet()
        self.update_summary()
        self.highlight_selection()

    def insert_carton(self, layer_idx, pos):
        """Insert a carton into the given layer at `pos`."""
        thickness = parse_dim(self.cardboard_thickness_var)
        if self.layers[layer_idx]:
            _, _, w, h = self.layers[layer_idx][0]
        else:
            w = parse_dim(self.box_w_var) + 2 * thickness
            h = parse_dim(self.box_l_var) + 2 * thickness
        self.layers[layer_idx].append((pos[0], pos[1], w, h))
        self.carton_ids[layer_idx].append(len(self.carton_ids[layer_idx]) + 1)
        next_id = max(self.carton_ids[layer_idx], default=0) + 1
        self.carton_ids[layer_idx].append(next_id)
        other_layer = 1 - layer_idx
        if (
            other_layer < len(self.layers)
            and self.layer_patterns[other_layer] == self.layer_patterns[layer_idx]
            and self.layers_linked()
        ):
            self.layers[other_layer].append((pos[0], pos[1], w, h))
            self.carton_ids[other_layer].append(len(self.carton_ids[other_layer]) + 1)
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
        if not self.selected_indices:
            return

        affected = set()
        for layer_idx, idx in sorted(
            self.selected_indices, key=lambda t: (t[0], -t[1])
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

        self.selected_indices.clear()
        self.drag_info = None
        getattr(self, "sort_layers", lambda: None)()
        self.draw_pallet()
        self.update_summary()
        self.highlight_selection()

    def rotate_selected_carton(self):
        """Rotate all selected cartons by 90° around their centers."""
        if not self.selected_indices:
            return

        for layer_idx, idx in list(self.selected_indices):
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
        if not self.selected_indices:
            return

        layer_idx = next(iter(self.selected_indices))[0]
        indices = [i for layer, i in self.selected_indices if layer == layer_idx]
        if not indices:
            return

        pallet_w = parse_dim(self.pallet_w_var)
        pallet_l = parse_dim(self.pallet_l_var)
        sel = [self.layers[layer_idx][i] for i in indices]
        span_x = max(x + w for x, y, w, h in sel) - min(x for x, y, w, h in sel)
        span_y = max(y + h for x, y, w, h in sel) - min(y for x, y, w, h in sel)
        orientation = "x" if span_x >= span_y else "y"
        start = 0
        end = pallet_w if orientation == "x" else pallet_l
        TabPallet._distribute(self, layer_idx, indices, start, end, orientation)
        getattr(self, "sort_layers", lambda: None)()
        self.draw_pallet()
        self.update_summary()

    def auto_space_selected(self):
        if not self.selected_indices:
            return

        layer_idx = next(iter(self.selected_indices))[0]
        indices = [i for layer, i in self.selected_indices if layer == layer_idx]
        if not indices:
            return

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
        if not self.selected_indices:
            return

        layer_idx = next(iter(self.selected_indices))[0]
        indices = [i for layer, i in self.selected_indices if layer == layer_idx]
        if not indices:
            return

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

    def on_right_click(self, event):
        if not self.modify_mode_var.get() or event.inaxes not in [
            self.ax_odd,
            self.ax_even,
        ]:
            return
        self.context_layer = 0 if event.inaxes is self.ax_odd else 1
        if event.xdata is not None and event.ydata is not None:
            self.context_pos = (event.xdata, event.ydata)

        # Automatically select the carton under the cursor unless it is already
        # part of the current selection. This allows context menu actions to be
        # applied to multiple cartons when right-clicking on any of them.
        found = False
        for patch, idx in self.patches[self.context_layer]:
            contains, _ = patch.contains(event)
            if contains:
                if (self.context_layer, idx) not in self.selected_indices:
                    self.selected_indices = {(self.context_layer, idx)}
                found = True
                break
        if not found:
            self.selected_indices.clear()

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
                label="R\u00f3wnomiernie wzd\u0142u\u017c innych karton\u00f3w",
                command=self.distribute_selected_between,
            )
            self.context_menu.add_command(
                label="Automatyczny odst\u0119p", command=self.auto_space_selected
            )

        state = "normal" if self.selected_indices else "disabled"
        for i in range(1, 6):
            self.context_menu.entryconfigure(i, state=state if i > 0 else "normal")
        gui_ev = event.guiEvent
        if gui_ev:
            self.context_menu.tk_popup(int(gui_ev.x_root), int(gui_ev.y_root))
        self.highlight_selection()

    def update_summary(self):
        if not self.layers:
            self.totals_label.config(text="")
            self.materials_label.config(text="")
            self.weight_label.config(text="")
            return

        pallet_w = parse_dim(self.pallet_w_var)
        pallet_l = parse_dim(self.pallet_l_var)
        pallet_h = parse_dim(self.pallet_h_var)
        box_w = parse_dim(self.box_w_var)
        box_l = parse_dim(self.box_l_var)
        box_h = parse_dim(self.box_h_var)
        thickness = parse_dim(self.cardboard_thickness_var)
        slip_count = int(parse_dim(self.slip_count_var))

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
        total_products = total_cartons * self.products_per_carton
        num_slip = getattr(self, "slip_count", slip_count)
        stack_height = num_layers * box_h_ext
        if self.include_pallet_height_var.get():
            stack_height += pallet_h

        self.tape_per_carton = 4 * (box_w + box_l) / 1000
        self.film_per_pallet = 2 * (pallet_w + pallet_l) / 1000 * 6
        total_tape = total_cartons * self.tape_per_carton

        self.totals_label.config(
            text=f"Kartonów: {total_cartons} | Produkty: {total_products} | Wysokość: {stack_height:.1f} mm"
        )
        self.materials_label.config(
            text=f"Taśma: {total_tape:.2f} m | Folia: {self.film_per_pallet:.2f} m"
        )
        carton_wt = self.carton_weights.get(self.carton_var.get(), 0)
        pallet_wt = (
            self.pallet_weights.get(self.pallet_var.get(), 0)
            if self.include_pallet_height_var.get()
            else 0
        )
        tape_wt = total_tape * self.material_weights.get("tape", 0)
        film_wt = self.film_per_pallet * self.material_weights.get("stretch_film", 0)
        slip_mass = self.slip_sheet_weight * num_slip
        total_mass = (
            carton_wt * total_cartons + tape_wt + film_wt + pallet_wt + slip_mass
        )
        self.weight_label.config(text=f"Masa: {total_mass:.2f} kg")

        pallet_area = pallet_w * pallet_l / 1_000_000
        carton_area = (box_w + 2 * thickness) * (box_l + 2 * thickness) / 1_000_000
        area_ratio = pallet_area / carton_area if carton_area > 0 else 0
        self.area_label.config(
            text=f"Pow. palety: {pallet_area:.2f} m² | Pow. kartonu: {carton_area:.2f} m² | Miejsca: {area_ratio:.2f}"
        )

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
    # Wolny enumeration helpers
    # ------------------------------------------------------------------

    def update_wolny_layout(self) -> None:
        if not self.wolny_solutions:
            return
        idx = self.layout_map.get("Wolny")
        if idx is None:
            return
        pallet_w = parse_dim(self.pallet_w_var)
        pallet_l = parse_dim(self.pallet_l_var)
        spacing = parse_dim(self.spacing_var)
        patt = apply_spacing(self.wolny_solutions[self.wolny_index], spacing)
        centered = self.center_layout(patt, pallet_w, pallet_l)
        self.layouts[idx] = (len(centered), centered, "Wolny")
        # When cycling through "Wolny" layouts make sure it is the active
        # pattern for both odd and even layers so the preview updates even if
        # another layout was previously selected.
        if hasattr(self, "odd_layout_var") and self.odd_layout_var.get() != "Wolny":
            self.odd_layout_var.set("Wolny")
        if hasattr(self, "even_layout_var") and self.even_layout_var.get() != "Wolny":
            self.even_layout_var.set("Wolny")
        self.update_layers(force=True)
        self.draw_pallet()

    def generate_wolny_solution(self) -> bool:
        """Attempt to generate a new Wolny layout via CP-SAT search."""
        pallet_w = parse_dim(self.pallet_w_var)
        pallet_l = parse_dim(self.pallet_l_var)
        thickness = parse_dim(self.cardboard_thickness_var)
        spacing = parse_dim(self.spacing_var)
        box_w = parse_dim(self.box_w_var) + 2 * thickness
        box_l = parse_dim(self.box_l_var) + 2 * thickness
        res = algorithms.enumerate_packings_wolny(
            pallet_w,
            pallet_l,
            box_w + spacing,
            box_l + spacing,
            want=1,
            time_first=3,
            time_each=2,
        )
        if not res:
            return False
        sols, _ = res if isinstance(res, tuple) else (res, None)
        layout = sols[0]
        if layout in self.wolny_solutions:
            return False
        self.wolny_solutions.append(layout)
        self.wolny_index = len(self.wolny_solutions) - 1
        return True

    def next_wolny(self) -> None:
        if self.wolny_index + 1 < len(self.wolny_solutions):
            self.wolny_index += 1
        elif self.wolny_get_next:
            nxt = self.wolny_get_next()
            if nxt:
                self.wolny_solutions.append(nxt)
                self.wolny_index += 1
        else:
            self.generate_wolny_solution()
        self.update_wolny_layout()
        if self.wolny_index + 1 >= len(self.wolny_solutions) and not self.wolny_get_next:
            self.next_btn.state(["disabled"])
        else:
            self.next_btn.state(["!disabled"])
        if self.wolny_index > 0:
            self.prev_btn.state(["!disabled"])
        else:
            self.prev_btn.state(["disabled"])

    def prev_wolny(self) -> None:
        if self.wolny_index > 0:
            self.wolny_index -= 1
        self.update_wolny_layout()
        if self.wolny_index == 0:
            self.prev_btn.state(["disabled"])
        else:
            self.prev_btn.state(["!disabled"])
        if self.wolny_index + 1 >= len(self.wolny_solutions) and not self.wolny_get_next:
            self.next_btn.state(["disabled"])
        else:
            self.next_btn.state(["!disabled"])

    # ------------------------------------------------------------------
    # JSON pattern export / import helpers
    # ------------------------------------------------------------------

    def gather_pattern_data(self, name: str = "") -> dict:
        """Collect current pallet layout as a JSON-serialisable dict."""
        pallet_w = parse_dim(self.pallet_w_var)
        pallet_l = parse_dim(self.pallet_l_var)
        pallet_h = parse_dim(self.pallet_h_var)
        box_w = parse_dim(self.box_w_var)
        box_l = parse_dim(self.box_l_var)
        box_h = parse_dim(self.box_h_var)
        num_layers = getattr(self, "num_layers", int(parse_dim(self.num_layers_var)))
        data = {
            "name": name,
            "dimensions": {"width": pallet_w, "length": pallet_l, "height": pallet_h},
            "productDimensions": {"width": box_w, "length": box_l, "height": box_h},
            "layers": self.layers[:num_layers],
        }
        return data

    def apply_pattern_data(self, data: dict) -> None:
        """Load pallet layout from a dictionary."""
        dims = data.get("dimensions", {})
        self.pallet_w_var.set(str(dims.get("width", "")))
        self.pallet_l_var.set(str(dims.get("length", "")))
        self.pallet_h_var.set(str(dims.get("height", "")))
        prod = data.get("productDimensions", {})
        self.box_w_var.set(str(prod.get("width", "")))
        self.box_l_var.set(str(prod.get("length", "")))
        self.box_h_var.set(str(prod.get("height", "")))
        layers = data.get("layers", [])
        if layers:
            self.layers = [list(layer) for layer in layers]
            self.carton_ids = [list(range(1, len(layer) + 1)) for layer in self.layers]
            self.num_layers = len(self.layers)
            self.num_layers_var.set(str(self.num_layers))
            self.layer_patterns = ["" for _ in self.layers]
            self.transformations = ["Brak" for _ in self.layers]
            self.draw_pallet()
            self.update_summary()

    def save_pattern_dialog(self):
        name = simpledialog.askstring("Zapisz wzór", "Nazwa wzoru:")
        if not name:
            return
        data = self.gather_pattern_data(name)
        try:
            save_pattern(name, data)
            path = pattern_path(name)
            messagebox.showinfo("Sukces", f"Zapisano wzór '{name}' w {path}")
        except Exception as exc:
            messagebox.showerror("Błąd zapisu", str(exc))

    def load_pattern_dialog(self):
        _ensure_dir()
        path = filedialog.askopenfilename(
            title="Wczytaj wzór",
            initialdir=PATTERN_DIR,
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
