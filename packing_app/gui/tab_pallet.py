import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from packing_app.core.algorithms import pack_rectangles_mixed_greedy
from core.utils import load_cartons, load_pallets


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
        self.pack(fill=tk.BOTH, expand=True)
        self.layouts = []
        self.current_layout_idx = 0
        self.layers = []
        self.transformations = []
        self.transform_vars = []
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
        self.max_stack_var = tk.StringVar(value="0")
        entry_max_stack = ttk.Entry(layers_frame, textvariable=self.max_stack_var, width=8)
        entry_max_stack.grid(row=1, column=1, padx=5, pady=5)
        entry_max_stack.bind("<Return>", self.compute_pallet)
        self.include_pallet_height_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(layers_frame, text="Uwzględnij wysokość nośnika", variable=self.include_pallet_height_var, command=self.compute_pallet).grid(row=1, column=2, columnspan=2, padx=5, pady=5, sticky="w")

        ttk.Label(layers_frame, text="Centrowanie:").grid(row=0, column=2, padx=5, pady=5)
        self.center_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(layers_frame, variable=self.center_var, command=self.compute_pallet).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(layers_frame, text="Tryb:").grid(row=0, column=4, padx=5, pady=5)
        self.center_mode_var = tk.StringVar(value="Cała warstwa")
        ttk.OptionMenu(layers_frame, self.center_mode_var, "Cała warstwa", "Cała warstwa", "Poszczególne obszary").grid(row=0, column=5, padx=5, pady=5)

        self.alternate_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(layers_frame, text="Naprzemienne transformacje", variable=self.alternate_var, command=self.update_transformations).grid(row=0, column=6, padx=5, pady=5)

        self.transform_frame = ttk.Frame(layers_frame)
        self.transform_frame.grid(row=2, column=0, columnspan=7, padx=5, pady=5)

        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(control_frame, text="Oblicz", command=self.compute_pallet).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Poprzedni", command=self.prev_layout).pack(side=tk.LEFT, padx=5)
        self.layout_label = ttk.Label(control_frame, text="Układ 1")
        self.layout_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Następny", command=self.next_layout).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Pokaż w 3D", command=self.show_3d).pack(side=tk.LEFT, padx=5)

        self.summary_frame = ttk.LabelFrame(self, text="Obliczenia")
        self.summary_frame.pack(fill=tk.X, padx=10, pady=5)
        self.totals_label = ttk.Label(self.summary_frame, text="")
        self.totals_label.pack(side=tk.LEFT, padx=5)
        self.materials_label = ttk.Label(self.summary_frame, text="")
        self.materials_label.pack(side=tk.LEFT, padx=5)
        self.weight_label = ttk.Label(self.summary_frame, text="")
        self.weight_label.pack(side=tk.LEFT, padx=5)

        self.fig = plt.Figure(figsize=(8, 6))
        self.ax = self.fig.add_subplot(111)
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
        for i in range(int(parse_dim(self.num_layers_var))):
            ttk.Label(self.transform_frame, text=f"Warstwa {i+1}:").grid(row=i, column=0, padx=5, pady=2)
            var = tk.StringVar(value="Brak")
            ttk.OptionMenu(self.transform_frame, var, "Brak", "Brak", "Obrót 180° (dłuższy bok)", "Obrót 180° (krótszy bok)",
                           "Odbicie lustrzane (dłuższy bok)", "Odbicie lustrzane (krótszy bok)", command=self.update_transformations).grid(row=i, column=1, padx=5, pady=2)
            self.transform_vars.append(var)

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

    def prev_layout(self):
        if self.layouts:
            self.current_layout_idx = (self.current_layout_idx - 1) % len(self.layouts)
            self.update_layout()

    def next_layout(self):
        if self.layouts:
            self.current_layout_idx = (self.current_layout_idx + 1) % len(self.layouts)
            self.update_layout()

    def update_layout(self):
        self.layout_label.config(text=f"Układ {self.current_layout_idx + 1} z {len(self.layouts)}")
        self.draw_pallet()

    def update_transformations(self, *args):
        self.transformations = [var.get() for var in self.transform_vars]
        if self.alternate_var.get() and len(self.transform_vars) > 1:
            for i in range(len(self.transformations)):
                self.transformations[i] = self.transform_vars[1].get() if i % 2 else "Brak"
        self.draw_pallet()

    def apply_transformation(self, positions, transform, pallet_w, pallet_l, box_w, box_l):
        new_positions = []
        for x, y, w, h in positions:
            if transform == "Brak":
                new_positions.append((x, y, w, h))
            elif transform == "Obrót 180° (dłuższy bok)":
                new_x = pallet_w - x - w
                new_y = y
                new_positions.append((new_x, new_y, w, h))
            elif transform == "Obrót 180° (krótszy bok)":
                new_x = x
                new_y = pallet_l - y - h
                new_positions.append((new_x, new_y, w, h))
            elif transform == "Odbicie lustrzane (dłuższy bok)":
                new_x = pallet_w - x - w
                new_y = y
                new_positions.append((new_x, new_y, w, h))
            elif transform == "Odbicie lustrzane (krótszy bok)":
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
        num_layers = int(parse_dim(self.num_layers_var))
        max_stack = parse_dim(self.max_stack_var)

        if max_stack > 0:
            avail = max_stack - (pallet_h if self.include_pallet_height_var.get() else 0)
            box_h_ext = box_h + 2 * thickness
            if box_h_ext > 0:
                num_layers = int(avail // box_h_ext)
                self.num_layers_var.set(str(max(num_layers, 0)))

        if pallet_w == 0 or pallet_l == 0 or pallet_h == 0 or box_w == 0 or box_l == 0 or box_h == 0 or num_layers <= 0:
            messagebox.showwarning("Błąd", "Wszystkie wymiary i liczba warstw muszą być większe od 0.")
            return

        self.layouts = []
        count1, positions1 = pack_rectangles_mixed_greedy(pallet_w, pallet_l, box_w, box_l)
        positions1 = self.center_layout(positions1, pallet_w, pallet_l)
        self.layouts.append((count1, positions1, "Standardowy"))

        count2, positions2 = pack_rectangles_mixed_greedy(pallet_w, pallet_l, box_l, box_w)
        positions2 = self.center_layout(positions2, pallet_w, pallet_l)
        self.layouts.append((count2, positions2, "Naprzemienny"))

        self.transform_vars = []
        self.update_transform_frame()
        self.layers = []
        for _ in range(num_layers):
            count, positions, _ = self.layouts[self.current_layout_idx]
            self.layers.append(positions)
        self.update_transformations()
        if self.layers:
            box_h_ext = box_h + 2 * thickness
            total_cartons = len(self.layers[0]) * num_layers
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
            self.weight_label.config(text="")
        else:
            self.totals_label.config(text="")
            self.materials_label.config(text="")
            self.weight_label.config(text="")

    def draw_pallet(self):
        self.ax.clear()
        pallet_w = parse_dim(self.pallet_w_var)
        pallet_l = parse_dim(self.pallet_l_var)
        self.ax.add_patch(plt.Rectangle((0, 0), pallet_w, pallet_l, fill=False, edgecolor='black', linewidth=2))
        for layer_idx, positions in enumerate(self.layers):
            transformed = self.apply_transformation(positions, self.transformations[layer_idx], pallet_w, pallet_l, parse_dim(self.box_w_var) + 2 * parse_dim(self.cardboard_thickness_var), parse_dim(self.box_l_var) + 2 * parse_dim(self.cardboard_thickness_var))
            for x, y, w, h in transformed:
                color = 'blue' if layer_idx % 2 == 0 else 'green'
                self.ax.add_patch(plt.Rectangle((x, y), w, h, fill=True, facecolor=color, alpha=0.5, edgecolor='black'))
        self.ax.set_xlim(-50, pallet_w + 50)
        self.ax.set_ylim(-50, pallet_l + 50)
        self.ax.set_aspect('equal')
        self.ax.set_title(f"Liczba kartonów w warstwie: {len(self.layers[0])}")
        self.canvas.draw()

    def show_3d(self):
        window = tk.Toplevel(self)
        window.title("Widok 3D")
        fig_3d = plt.Figure(figsize=(8, 6))
        ax_3d = fig_3d.add_subplot(111, projection='3d')
        canvas_3d = FigureCanvasTkAgg(fig_3d, master=window)
        canvas_3d.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        toolbar_3d = NavigationToolbar2Tk(canvas_3d, window)
        toolbar_3d.update()

        pallet_w = parse_dim(self.pallet_w_var)
        pallet_l = parse_dim(self.pallet_l_var)
        pallet_h = parse_dim(self.pallet_h_var)
        box_w = parse_dim(self.box_w_var)
        box_l = parse_dim(self.box_l_var)
        box_h = parse_dim(self.box_h_var)
        thickness = parse_dim(self.cardboard_thickness_var)

        box_w_ext = box_w + 2 * thickness
        box_l_ext = box_l + 2 * thickness
        box_h_ext = box_h + 2 * thickness

        ax_3d.bar3d([0], [0], [0], [pallet_w], [pallet_l], [50], color='red', alpha=0.2)
        for layer_idx, positions in enumerate(self.layers):
            transformed = self.apply_transformation(positions, self.transformations[layer_idx], pallet_w, pallet_l, box_w_ext, box_l_ext)
            xs = [x for x, y, w, h in transformed]
            ys = [y for x, y, w, h in transformed]
            zs = [layer_idx * box_h_ext] * len(transformed)
            dxs = [w for x, y, w, h in transformed]
            dys = [h for x, y, w, h in transformed]
            dzs = [box_h_ext] * len(transformed)
            color = plt.cm.tab10(layer_idx % 10)
            ax_3d.bar3d(xs, ys, zs, dxs, dys, dzs, color=color, alpha=0.7)

        ax_3d.set_xlim(0, pallet_w)
        ax_3d.set_ylim(0, pallet_l)
        ax_3d.set_zlim(0, pallet_h)
        ax_3d.set_xlabel('W (mm)')
        ax_3d.set_ylabel('L (mm)')
        ax_3d.set_zlabel('H (mm)')
        canvas_3d.draw()

