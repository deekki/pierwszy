import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from packing_app.core.algorithms import (
    pack_rectangles_mixed_greedy,
    compute_interlocked_layout,
    compute_brick_layout,
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
        self.pallet_weights = {p['name']: p['weight'] for p in load_pallets_with_weights()}
        self.material_weights = load_materials()
        self.pack(fill=tk.BOTH, expand=True)
        self.layouts = []
        self.layers = []
        self.transformations = []
        self.products_per_carton = 1
        self.tape_per_carton = 0.0
        self.film_per_pallet = 0.0
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
        entry_pallet_w = ttk.Entry(pallet_frame, textvariable=self.pallet_w_var, width=10)
        entry_pallet_w.grid(row=0, column=3, padx=5, pady=5)
        entry_pallet_w.bind("<Return>", self.compute_pallet)

        ttk.Label(pallet_frame, text="L (mm):").grid(row=0, column=4, padx=5, pady=5)
        self.pallet_l_var = tk.StringVar(value=str(self.predefined_pallets[0]["l"]))
        entry_pallet_l = ttk.Entry(pallet_frame, textvariable=self.pallet_l_var, width=10)
        entry_pallet_l.grid(row=0, column=5, padx=5, pady=5)
        entry_pallet_l.bind("<Return>", self.compute_pallet)

        ttk.Label(pallet_frame, text="H (mm):").grid(row=0, column=6, padx=5, pady=5)
        self.pallet_h_var = tk.StringVar(value=str(self.predefined_pallets[0]["h"]))
        entry_pallet_h = ttk.Entry(pallet_frame, textvariable=self.pallet_h_var, width=10)
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
        self.box_w_var = tk.StringVar(value=str(self.predefined_cartons[list(self.predefined_cartons.keys())[0]][0]))
        entry_box_w = ttk.Entry(carton_frame, textvariable=self.box_w_var, width=10)
        entry_box_w.grid(row=0, column=3, padx=5, pady=5)
        entry_box_w.bind("<Return>", self.compute_pallet)

        ttk.Label(carton_frame, text="L (mm):").grid(row=0, column=4, padx=5, pady=5)
        self.box_l_var = tk.StringVar(value=str(self.predefined_cartons[list(self.predefined_cartons.keys())[0]][1]))
        entry_box_l = ttk.Entry(carton_frame, textvariable=self.box_l_var, width=10)
        entry_box_l.grid(row=0, column=5, padx=5, pady=5)
        entry_box_l.bind("<Return>", self.compute_pallet)

        ttk.Label(carton_frame, text="H (mm):").grid(row=0, column=6, padx=5, pady=5)
        self.box_h_var = tk.StringVar(value=str(self.predefined_cartons[list(self.predefined_cartons.keys())[0]][2]))
        entry_box_h = ttk.Entry(carton_frame, textvariable=self.box_h_var, width=10)
        entry_box_h.grid(row=0, column=7, padx=5, pady=5)
        entry_box_h.bind("<Return>", self.compute_pallet)

        ttk.Label(carton_frame, text="Grubość tektury (mm):").grid(row=1, column=0, padx=5, pady=5)
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

        ttk.Label(carton_frame, text="Wymiary zewnętrzne (mm):").grid(row=1, column=2, padx=5, pady=5)
        self.ext_dims_label = ttk.Label(carton_frame, text="")
        self.ext_dims_label.grid(row=1, column=3, columnspan=5, padx=5, pady=5, sticky="w")
        self.cardboard_thickness_var.trace_add("write", self.update_external_dimensions)
        self.box_w_var.trace_add("write", self.update_external_dimensions)
        self.box_l_var.trace_add("write", self.update_external_dimensions)
        self.box_h_var.trace_add("write", self.update_external_dimensions)

        layers_frame = ttk.LabelFrame(self, text="Ustawienia warstw")
        layers_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(layers_frame, text="Liczba warstw:").grid(row=0, column=0, padx=5, pady=5)
        self.num_layers_var = tk.StringVar(value="1")
        entry_num_layers = ttk.Entry(layers_frame, textvariable=self.num_layers_var, width=5)
        entry_num_layers.grid(row=0, column=1, padx=5, pady=5)
        entry_num_layers.bind("<Return>", self.compute_pallet)

        ttk.Label(layers_frame, text="Maksymalna wysokość ułożenia (mm):").grid(row=1, column=0, padx=5, pady=5)
        # Default maximum stack height is 1600 mm which roughly corresponds to
        # a common limit for palletized loads. Set to 0 to disable the limit.
        self.max_stack_var = tk.StringVar(value="1600")
        entry_max_stack = ttk.Entry(layers_frame, textvariable=self.max_stack_var, width=8)
        entry_max_stack.grid(row=1, column=1, padx=5, pady=5)
        entry_max_stack.bind("<Return>", self.compute_pallet)
        self.include_pallet_height_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(layers_frame, text="Uwzględnij wysokość nośnika", variable=self.include_pallet_height_var, command=self.compute_pallet).grid(row=1, column=2, columnspan=2, padx=5, pady=5, sticky="w")

        self.shift_even_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            layers_frame,
            text="Przesuwaj warstwy parzyste",
            variable=self.shift_even_var,
            command=self.compute_pallet,
        ).grid(row=1, column=4, columnspan=2, padx=5, pady=5, sticky="w")

        ttk.Label(layers_frame, text="Centrowanie:").grid(row=0, column=2, padx=5, pady=5)
        self.center_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(layers_frame, variable=self.center_var, command=self.compute_pallet).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(layers_frame, text="Tryb:").grid(row=0, column=4, padx=5, pady=5)
        self.center_mode_var = tk.StringVar(value="Cała warstwa")
        ttk.OptionMenu(layers_frame, self.center_mode_var, "Cała warstwa", "Cała warstwa", "Poszczególne obszary").grid(row=0, column=5, padx=5, pady=5)



        self.transform_frame = ttk.Frame(layers_frame)
        self.transform_frame.grid(row=2, column=0, columnspan=7, padx=5, pady=5)

        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(control_frame, text="Oblicz", command=self.compute_pallet).pack(side=tk.LEFT, padx=5)

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

        odd_default = layout_options[0]
        even_default = layout_options[0]
        if prev_odd_layout and prev_odd_layout.get() in layout_options:
            odd_default = prev_odd_layout.get()
        if prev_even_layout and prev_even_layout.get() in layout_options:
            even_default = prev_even_layout.get()
        odd_tr_default = prev_odd_transform.get() if prev_odd_transform else transform_options[0]
        even_tr_default = prev_even_transform.get() if prev_even_transform else transform_options[0]

        ttk.Label(self.transform_frame, text="Warstwy nieparzyste:").grid(row=0, column=0, padx=5, pady=2)
        self.odd_layout_var = tk.StringVar(value=odd_default)
        ttk.OptionMenu(self.transform_frame, self.odd_layout_var, odd_default, *layout_options, command=self.update_layers).grid(row=0, column=1, padx=5, pady=2)
        self.odd_transform_var = tk.StringVar(value=odd_tr_default)
        ttk.OptionMenu(self.transform_frame, self.odd_transform_var, odd_tr_default, *transform_options, command=self.update_layers).grid(row=0, column=2, padx=5, pady=2)

        ttk.Label(self.transform_frame, text="Warstwy parzyste:").grid(row=1, column=0, padx=5, pady=2)
        self.even_layout_var = tk.StringVar(value=even_default)
        ttk.OptionMenu(self.transform_frame, self.even_layout_var, even_default, *layout_options, command=self.update_layers).grid(row=1, column=1, padx=5, pady=2)
        self.even_transform_var = tk.StringVar(value=even_tr_default)
        ttk.OptionMenu(self.transform_frame, self.even_transform_var, even_tr_default, *transform_options, command=self.update_layers).grid(row=1, column=2, padx=5, pady=2)

    def update_layers(self, *args):
        num_layers = getattr(self, 'num_layers', int(parse_dim(self.num_layers_var)))
        self.layers = []
        self.transformations = []
        odd_idx = self.layout_map.get(self.odd_layout_var.get(), 0)
        even_idx = self.layout_map.get(self.even_layout_var.get(), 0)
        for i in range(1, num_layers + 1):
            if i % 2 == 1:
                self.layers.append(self.layouts[odd_idx][1])
                transform = self.odd_transform_var.get()
            else:
                self.layers.append(self.layouts[even_idx][1])
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



    def apply_transformation(self, positions, transform, pallet_w, pallet_l, box_w, box_l):
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
        groups = []
        used = set()
        for i, (x1, y1, w1, h1) in enumerate(positions):
            if i in used:
                continue
            current_group = [(x1, y1, w1, h1)]
            used.add(i)
            for j, (x2, y2, w2, h2) in enumerate(positions):
                if j not in used and (abs(x1 - x2) < w1 or abs(y1 - y2) < h1):
                    current_group.append((x2, y2, w2, h2))
                    used.add(j)
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
                centered_positions.extend([(x + offset_x, y + offset_y, w, h) for x, y, w, h in group])
            return centered_positions

    def compute_pallet(self, event=None):
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

        if pallet_w == 0 or pallet_l == 0 or pallet_h == 0 or box_w == 0 or box_l == 0 or box_h == 0 or num_layers <= 0:
            messagebox.showwarning("Błąd", "Wszystkie wymiary i liczba warstw muszą być większe od 0.")
            return

        self.layouts = []
        count1, positions1 = pack_rectangles_mixed_greedy(
            pallet_w,
            pallet_l,
            box_w_ext,
            box_l_ext,
        )
        positions1 = self.center_layout(positions1, pallet_w, pallet_l)
        self.layouts.append((count1, positions1, "Standardowy"))

        count2, positions2 = pack_rectangles_mixed_greedy(
            pallet_w,
            pallet_l,
            box_l_ext,
            box_w_ext,
        )
        positions2 = self.center_layout(positions2, pallet_w, pallet_l)
        self.layouts.append((count2, positions2, "Naprzemienny"))

        _, _, interlocked_layers = compute_interlocked_layout(
            pallet_w,
            pallet_l,
            box_w_ext,
            box_l_ext,
            num_layers=2,
            shift_even=self.shift_even_var.get(),
        )
        idx_shifted = 1 if self.shift_even_var.get() else 0
        shifted = self.center_layout(interlocked_layers[idx_shifted], pallet_w, pallet_l)
        self.layouts.append((len(shifted), shifted, "Przesunięty"))

        count_brick, positions_brick = compute_brick_layout(
            pallet_w,
            pallet_l,
            box_w_ext,
            box_l_ext,
        )
        positions_brick = self.center_layout(positions_brick, pallet_w, pallet_l)
        self.layouts.append((count_brick, positions_brick, "Cegiełka"))

        self.layout_map = {name: idx for idx, (_, __, name) in enumerate(self.layouts)}
        self.update_transform_frame()
        self.num_layers = num_layers
        self.update_layers()
        if self.layers:
            box_h_ext = box_h + 2 * thickness
            cartons_per_odd = len(self.layers[0]) if self.layers else 0
            cartons_per_even = len(self.layers[1]) if len(self.layers) > 1 else cartons_per_odd
            total_cartons = 0
            for i in range(1, num_layers + 1):
                total_cartons += cartons_per_odd if i % 2 == 1 else cartons_per_even
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
            pallet_wt = self.pallet_weights.get(self.pallet_var.get(), 0) if self.include_pallet_height_var.get() else 0
            tape_wt = total_tape * self.material_weights.get("tape", 0)
            film_wt = self.film_per_pallet * self.material_weights.get("stretch_film", 0)
            total_mass = carton_wt * total_cartons + tape_wt + film_wt + pallet_wt
            self.weight_label.config(text=f"Masa: {total_mass:.2f} kg")
        else:
            self.totals_label.config(text="")
            self.materials_label.config(text="")
            self.weight_label.config(text="")

    def draw_pallet(self):
        pallet_w = parse_dim(self.pallet_w_var)
        pallet_l = parse_dim(self.pallet_l_var)
        axes = [self.ax_odd, self.ax_even]
        labels = ["Warstwa nieparzysta", "Warstwa parzysta"]
        for idx, ax in enumerate(axes):
            ax.clear()
            ax.add_patch(plt.Rectangle((0, 0), pallet_w, pallet_l, fill=False, edgecolor='black', linewidth=2))
            if idx < len(self.layers):
                transformed = self.apply_transformation(
                    self.layers[idx],
                    self.transformations[idx],
                    pallet_w,
                    pallet_l,
                    parse_dim(self.box_w_var) + 2 * parse_dim(self.cardboard_thickness_var),
                    parse_dim(self.box_l_var) + 2 * parse_dim(self.cardboard_thickness_var),
                )
                for x, y, w, h in transformed:
                    color = 'blue' if idx == 0 else 'green'
                    ax.add_patch(
                        plt.Rectangle((x, y), w, h, fill=True, facecolor=color, alpha=0.5, edgecolor='black')
                    )
                ax.set_title(f"{labels[idx]}: {len(self.layers[idx])}")
            ax.set_xlim(-50, pallet_w + 50)
            ax.set_ylim(-50, pallet_l + 50)
            ax.set_aspect('equal')
        self.canvas.draw()

