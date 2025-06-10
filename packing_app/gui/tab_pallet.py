import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
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
)


def parse_dim(var: tk.StringVar) -> float:
    try:
        val = float(var.get().replace(",", "."))
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
        self.pack(fill=tk.BOTH, expand=True)
        self.layouts = []
        self.layers = []
        self.transformations = []
        self.products_per_carton = 1
        self.tape_per_carton = 0.0
        self.film_per_pallet = 0.0
        self.best_layout_name = ""
        self.best_even = []
        self.best_odd = []
        self.modify_mode_var = tk.BooleanVar(value=False)
        self.patches = []
        self.selected_patch = None
        self.drag_offset = (0, 0)
        self.press_cid = None
        self.motion_cid = None
        self.release_cid = None
        self.context_menu = None
        self.context_layer = 0
        self.context_pos = (0, 0)
        self.build_ui()

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

        self.transform_frame = ttk.Frame(layers_frame)
        self.transform_frame.grid(row=2, column=0, columnspan=7, padx=5, pady=5)

        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        self.compute_btn = ttk.Button(
            control_frame, text="Oblicz", command=self.compute_pallet
        )
        self.compute_btn.pack(side=tk.LEFT, padx=5)
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
        self.status_var = tk.StringVar(value="")
        self.status_label = ttk.Label(control_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT, padx=5)

        self.summary_frame = ttk.LabelFrame(self, text="Obliczenia")
        self.summary_frame.pack(fill=tk.X, padx=10, pady=5)
        self.totals_label = ttk.Label(self.summary_frame, text="")
        self.totals_label.pack(side=tk.LEFT, padx=5)
        self.materials_label = ttk.Label(self.summary_frame, text="")
        self.materials_label.pack(side=tk.LEFT, padx=5)
        self.weight_label = ttk.Label(self.summary_frame, text="")
        self.weight_label.pack(side=tk.LEFT, padx=5)

        self.fig = plt.Figure(figsize=(8, 6))
        self.ax_odd = self.fig.add_subplot(121)
        self.ax_even = self.fig.add_subplot(122)
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
        even_tr_default = (
            prev_even_transform.get() if prev_even_transform else transform_options[0]
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
            command=self.update_layers,
        ).grid(row=0, column=1, padx=5, pady=2)
        self.odd_transform_var = tk.StringVar(value=odd_tr_default)
        ttk.OptionMenu(
            self.transform_frame,
            self.odd_transform_var,
            odd_tr_default,
            *transform_options,
            command=self.update_layers,
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
            command=self.update_layers,
        ).grid(row=1, column=1, padx=5, pady=2)
        self.even_transform_var = tk.StringVar(value=even_tr_default)
        ttk.OptionMenu(
            self.transform_frame,
            self.even_transform_var,
            even_tr_default,
            *transform_options,
            command=self.update_layers,
        ).grid(row=1, column=2, padx=5, pady=2)

    def update_layers(self, *args):
        num_layers = getattr(self, "num_layers", int(parse_dim(self.num_layers_var)))
        self.layers = []
        self.transformations = []
        odd_name = self.odd_layout_var.get()
        even_name = self.even_layout_var.get()
        odd_idx = self.layout_map.get(odd_name, 0)
        even_idx = self.layout_map.get(even_name, 0)
        odd_layout = (
            self.best_odd
            if odd_name == self.best_layout_name
            else self.layouts[odd_idx][1]
        )
        even_layout = (
            self.best_even
            if even_name == self.best_layout_name
            else self.layouts[even_idx][1]
        )
        for i in range(1, num_layers + 1):
            if i % 2 == 1:
                self.layers.append(odd_layout)
                transform = self.odd_transform_var.get()
            else:
                self.layers.append(even_layout)
                transform = self.even_transform_var.get()
            self.transformations.append(transform)
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

    def apply_transformation(
        self, positions, transform, pallet_w, pallet_l, box_w, box_l
    ):
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
                return [
                    (x + offset_x, y + offset_y, w, h)
                    for x, y, w, h in positions
                ]
            return centered_positions

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
            box_w_ext = box_w + 2 * thickness
            box_l_ext = box_l + 2 * thickness
            num_layers = int(parse_dim(self.num_layers_var))
            max_stack = parse_dim(self.max_stack_var)

            if max_stack > 0:
                avail = max_stack - (
                    pallet_h if self.include_pallet_height_var.get() else 0
                )
                box_h_ext = box_h + 2 * thickness
                if box_h_ext > 0:
                    num_layers = max(int(avail // box_h_ext), 0)
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

            carton = Carton(box_w_ext, box_l_ext, box_h)
            pallet = Pallet(pallet_w, pallet_l, pallet_h)
            selector = PatternSelector(carton, pallet)

            patterns, best_name, self.best_even, self.best_odd = self._get_default_layout(
                selector,
                carton,
                pallet,
                pallet_w,
                pallet_l,
            )

            for name, patt in patterns.items():
                centered = self.center_layout(patt, pallet_w, pallet_l)
                display = name.replace("_", " ").capitalize()
                self.layouts.append((len(centered), centered, display))

            self.best_layout_name = best_name
            # Force the interlock pattern to be the default selection when
            # available.  Fallback to the best scored pattern otherwise.
            if "interlock" in patterns:
                best_name = "interlock"
                best_pattern = patterns["interlock"]
            else:
                best_name, best_pattern, _ = selector.best(
                    maximize_mixed=self.maximize_mixed.get()
                )

            seq = EvenOddSequencer(best_pattern, carton, pallet)
            even_base, odd_shifted = seq.best_shift()
            if self.shift_even_var.get():
                self.best_even = self.center_layout(odd_shifted, pallet_w, pallet_l)
                self.best_odd = self.center_layout(even_base, pallet_w, pallet_l)
            else:
                self.best_even = self.center_layout(even_base, pallet_w, pallet_l)
                self.best_odd = self.center_layout(odd_shifted, pallet_w, pallet_l)
            self.best_layout_name = best_name.replace("_", " ").capitalize()


            self.layout_map = {
                name: idx for idx, (_, __, name) in enumerate(self.layouts)
            }
            self.update_transform_frame()
            self.num_layers = num_layers
            self.update_layers()
            self.update_summary()
        finally:
            if hasattr(self, "status_var"):
                self.status_var.set("")
            if hasattr(self, "compute_btn"):
                self.compute_btn.state(["!disabled"])

    def draw_pallet(self):
        pallet_w = parse_dim(self.pallet_w_var)
        pallet_l = parse_dim(self.pallet_l_var)
        axes = [self.ax_odd, self.ax_even]
        labels = ["Warstwa nieparzysta", "Warstwa parzysta"]
        self.patches = [[] for _ in axes]
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
            if idx < len(self.layers):
                # Work on a copy so stored layers remain untouched when not in
                # modify mode.  This prevents cumulative transformations when
                # `draw_pallet` is called repeatedly.
                coords = list(self.layers[idx])
                if not self.modify_mode_var.get():
                    coords = self.apply_transformation(
                        coords,
                        self.transformations[idx],
                        pallet_w,
                        pallet_l,
                        parse_dim(self.box_w_var)
                        + 2 * parse_dim(self.cardboard_thickness_var),
                        parse_dim(self.box_l_var)
                        + 2 * parse_dim(self.cardboard_thickness_var),
                    )
                for i, (x, y, w, h) in enumerate(coords):
                    color = "blue" if idx == 0 else "green"
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
                ax.set_title(f"{labels[idx]}: {len(self.layers[idx])}")
            ax.set_xlim(-50, pallet_w + 50)
            ax.set_ylim(-50, pallet_l + 50)
            ax.set_aspect("equal")
        self.canvas.draw()
        if hasattr(self, "status_var"):
            self.status_var.set("")
        if hasattr(self, "compute_btn"):
            self.compute_btn.state(["!disabled"])

    def toggle_edit_mode(self):
        if self.modify_mode_var.get():
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
            self.selected_patch = None
            self.draw_pallet()

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
                x, y = patch.get_xy()
                self.selected_patch = (layer_idx, idx, patch)
                self.drag_offset = (x - event.xdata, y - event.ydata)
                break

    def on_motion(self, event):
        if not self.selected_patch or event.xdata is None or event.ydata is None:
            return
        layer_idx, idx, patch = self.selected_patch
        new_x = event.xdata + self.drag_offset[0]
        new_y = event.ydata + self.drag_offset[1]
        patch.set_xy((new_x, new_y))
        x, y, w, h = self.layers[layer_idx][idx]
        self.layers[layer_idx][idx] = (new_x, new_y, w, h)
        self.canvas.draw_idle()

    def on_release(self, event):
        if self.selected_patch:
            self.selected_patch = None
            self.draw_pallet()
            self.update_summary()

    def insert_carton(self, layer_idx, pos):
        """Insert a carton into the given layer at `pos`."""
        thickness = parse_dim(self.cardboard_thickness_var)
        if self.layers[layer_idx]:
            _, _, w, h = self.layers[layer_idx][0]
        else:
            w = parse_dim(self.box_w_var) + 2 * thickness
            h = parse_dim(self.box_l_var) + 2 * thickness
        self.layers[layer_idx].append((pos[0], pos[1], w, h))
        self.draw_pallet()
        self.update_summary()

    def insert_carton_button(self):
        self.insert_carton(self.context_layer, self.context_pos)

    def delete_selected_carton(self):
        if self.selected_patch:
            layer_idx, idx, _ = self.selected_patch
            del self.layers[layer_idx][idx]
            self.selected_patch = None
            self.draw_pallet()
            self.update_summary()

    def on_right_click(self, event):
        if not self.modify_mode_var.get() or event.inaxes not in [self.ax_odd, self.ax_even]:
            return
        self.context_layer = 0 if event.inaxes is self.ax_odd else 1
        if event.xdata is not None and event.ydata is not None:
            self.context_pos = (event.xdata, event.ydata)
        if self.context_menu is None:
            self.context_menu = tk.Menu(self, tearoff=0)
            self.context_menu.add_command(label="Wstaw karton", command=self.insert_carton_button)
            self.context_menu.add_command(label="Usu\u0144 karton", command=self.delete_selected_carton)
        state = "normal" if self.selected_patch else "disabled"
        self.context_menu.entryconfigure(1, state=state)
        gui_ev = event.guiEvent
        if gui_ev:
            self.context_menu.tk_popup(int(gui_ev.x_root), int(gui_ev.y_root))

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
        total_mass = carton_wt * total_cartons + tape_wt + film_wt + pallet_wt
        self.weight_label.config(text=f"Masa: {total_mass:.2f} kg")
