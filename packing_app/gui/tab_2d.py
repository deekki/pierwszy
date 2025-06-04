import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from packing_app.core.algorithms import (
    pack_rectangles_2d,
    pack_rectangles_mixed_greedy,
    maximize_mixed_layout,
    place_air_cushions,
    pack_circles_grid_bottomleft,
    pack_hex_top_down,
    pack_hex_bottom_up,
)
from core.utils import load_cartons

class TabPacking2D(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.style = ttk.Style()
        self.style.configure("Selected.TRadiobutton", background="#e0f0e0")
        self.style.configure("Unselected.TRadiobutton", background="")
        self.predefined_cartons = load_cartons()
        self.updating_carton = False
        self.prev_prod_h_rect = "0"
        self.prev_prod_h_circle = "0"
        self.build_ui()

    def build_ui(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        gui_frame = ttk.Frame(main_frame)
        gui_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        sections_frame = ttk.Frame(gui_frame)
        sections_frame.pack(side=tk.TOP, fill=tk.X)

        f_carton = ttk.LabelFrame(sections_frame, text="Karton")
        f_carton.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)

        f_carton_row1 = ttk.Frame(f_carton)
        f_carton_row1.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        ttk.Label(f_carton_row1, text="Wybierz karton:").pack(side=tk.LEFT, padx=5)
        self.carton_choice = tk.StringVar(value="Manual")
        self.cb_carton = ttk.Combobox(f_carton_row1, textvariable=self.carton_choice, state="readonly", width=30)
        self.cb_carton.pack(side=tk.LEFT, padx=5)
        self.cb_carton.bind("<<ComboboxSelected>>", self.on_carton_selected)

        f_carton_row2 = ttk.Frame(f_carton)
        f_carton_row2.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        ttk.Label(f_carton_row2, text="Szerokość [mm]:").pack(side=tk.LEFT, padx=5)
        self.carton_w = tk.StringVar(value="300")
        entry_carton_w = ttk.Entry(f_carton_row2, textvariable=self.carton_w, width=8, validate="key", validatecommand=(self.register(self.validate_number), "%P"))
        entry_carton_w.pack(side=tk.LEFT, padx=5)
        entry_carton_w.bind("<Return>", self.on_enter_pressed)

        f_carton_row3 = ttk.Frame(f_carton)
        f_carton_row3.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        ttk.Label(f_carton_row3, text="Długość [mm]:").pack(side=tk.LEFT, padx=5)
        self.carton_l = tk.StringVar(value="200")
        entry_carton_l = ttk.Entry(f_carton_row3, textvariable=self.carton_l, width=8, validate="key", validatecommand=(self.register(self.validate_number), "%P"))
        entry_carton_l.pack(side=tk.LEFT, padx=5)
        entry_carton_l.bind("<Return>", self.on_enter_pressed)

        f_carton_row4 = ttk.Frame(f_carton)
        f_carton_row4.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        ttk.Label(f_carton_row4, text="Wysokość [mm]:").pack(side=tk.LEFT, padx=5)
        self.carton_h = tk.StringVar(value="0")
        entry_carton_h = ttk.Entry(f_carton_row4, textvariable=self.carton_h, width=8, validate="key", validatecommand=(self.register(self.validate_number), "%P"))
        entry_carton_h.pack(side=tk.LEFT, padx=5)
        entry_carton_h.bind("<Return>", self.on_enter_pressed)

        f_prod = ttk.LabelFrame(sections_frame, text="Produkt")
        f_prod.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)

        f_type = ttk.LabelFrame(f_prod, text="Typ produktu")
        f_type.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        self.prod_type = tk.StringVar(value="rectangle")
        self.prod_type.trace_add("write", lambda *args: self.update_product_fields())
        self.rb_rect = ttk.Radiobutton(f_type, text="Kartoniki", variable=self.prod_type, value="rectangle", command=self.update_product_fields, style="Selected.TRadiobutton")
        self.rb_rect.pack(side=tk.LEFT, padx=5)
        self.rb_circle = ttk.Radiobutton(f_type, text="Pojemniki/Butelki", variable=self.prod_type, value="circle", command=self.update_product_fields, style="Unselected.TRadiobutton")
        self.rb_circle.pack(side=tk.LEFT, padx=5)

        f_product_fields = ttk.Frame(f_prod)
        f_product_fields.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        self.f_rect_container = ttk.LabelFrame(f_product_fields, text="Kartoniki")
        self.f_rect_container.pack(side=tk.LEFT, fill=tk.X, padx=5)

        f_rect_row1 = ttk.Frame(self.f_rect_container)
        f_rect_row1.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        ttk.Label(f_rect_row1, text="Długość kartonika [mm]:").pack(side=tk.LEFT, padx=5)
        self.prod_w = tk.StringVar(value="50")
        entry_prod_w = ttk.Entry(f_rect_row1, textvariable=self.prod_w, width=8, validate="key", validatecommand=(self.register(self.validate_number), "%P"))
        entry_prod_w.pack(side=tk.LEFT, padx=5)
        entry_prod_w.bind("<Return>", self.on_enter_pressed)

        f_rect_row2 = ttk.Frame(self.f_rect_container)
        f_rect_row2.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        ttk.Label(f_rect_row2, text="Szerokość kartonika [mm]:").pack(side=tk.LEFT, padx=5)
        self.prod_l = tk.StringVar(value="30")
        entry_prod_l = ttk.Entry(f_rect_row2, textvariable=self.prod_l, width=8, validate="key", validatecommand=(self.register(self.validate_number), "%P"))
        entry_prod_l.pack(side=tk.LEFT, padx=5)
        entry_prod_l.bind("<Return>", self.on_enter_pressed)

        f_rect_row3 = ttk.Frame(self.f_rect_container)
        f_rect_row3.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        ttk.Label(f_rect_row3, text="Wysokość kartonika [mm]:").pack(side=tk.LEFT, padx=5)
        self.prod_h_rect = tk.StringVar(value="0")
        entry_prod_h_rect = ttk.Entry(f_rect_row3, textvariable=self.prod_h_rect, width=8, validate="key", validatecommand=(self.register(self.validate_number), "%P"))
        entry_prod_h_rect.pack(side=tk.LEFT, padx=5)
        entry_prod_h_rect.bind("<Return>", self.on_enter_pressed)

        self.f_circle_container = ttk.LabelFrame(f_product_fields, text="Pojemniki/Butelki")
        self.f_circle_container.pack(side=tk.LEFT, fill=tk.X, padx=5)

        f_circle_row1 = ttk.Frame(self.f_circle_container)
        f_circle_row1.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        ttk.Label(f_circle_row1, text="Średnica pojemnika [mm]:").pack(side=tk.LEFT, padx=5)
        self.prod_diam = tk.StringVar(value="25")
        entry_prod_diam = ttk.Entry(f_circle_row1, textvariable=self.prod_diam, width=8, validate="key", validatecommand=(self.register(self.validate_number), "%P"))
        entry_prod_diam.pack(side=tk.LEFT, padx=5)
        entry_prod_diam.bind("<Return>", self.on_enter_pressed)

        f_circle_row2 = ttk.Frame(self.f_circle_container)
        f_circle_row2.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        ttk.Label(f_circle_row2, text="Wysokość pojemnika [mm]:").pack(side=tk.LEFT, padx=5)
        self.prod_h_circle = tk.StringVar(value="0")
        entry_prod_h_circle = ttk.Entry(f_circle_row2, textvariable=self.prod_h_circle, width=8, validate="key", validatecommand=(self.register(self.validate_number), "%P"))
        entry_prod_h_circle.pack(side=tk.LEFT, padx=5)
        entry_prod_h_circle.bind("<Return>", self.on_enter_pressed)

        f_settings = ttk.LabelFrame(sections_frame, text="Ustawienia dodatkowe")
        f_settings.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)

        f_settings_row1 = ttk.Frame(f_settings)
        f_settings_row1.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        ttk.Label(f_settings_row1, text="Minimalny luz (prawo/góra) [mm]:").pack(side=tk.LEFT, padx=5)
        self.margin = tk.StringVar(value="1")
        entry_margin = ttk.Entry(f_settings_row1, textvariable=self.margin, width=8, validate="key", validatecommand=(self.register(self.validate_number), "%P"))
        entry_margin.pack(side=tk.LEFT, padx=5)
        entry_margin.bind("<Return>", self.on_enter_pressed)

        f_settings_row2 = ttk.Frame(f_settings)
        f_settings_row2.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        self.use_cushions = tk.BooleanVar(value=False)
        ttk.Checkbutton(f_settings_row2, text="Dodaj poduszki z powietrzem", variable=self.use_cushions).pack(side=tk.LEFT, padx=5)
        ttk.Label(f_settings_row2, text="Wymiary poduszek: 37 x 175 x 110 mm").pack(side=tk.LEFT, padx=5)
        self.use_cushions.trace_add("write", lambda *args: self.show_packing())

        f_settings_row6 = ttk.Frame(f_settings)
        f_settings_row6.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        self.maximize_mixed = tk.BooleanVar(value=False)
        ttk.Checkbutton(f_settings_row6, text="Maksymalizuj układ mieszany", variable=self.maximize_mixed).pack(side=tk.LEFT, padx=5)
        self.maximize_mixed.trace_add("write", lambda *args: self.show_packing())

        f_settings_row3 = ttk.Frame(f_settings)
        f_settings_row3.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        ttk.Label(f_settings_row3, text="Minimalny odstęp między poduszkami [mm]:").pack(side=tk.LEFT, padx=5)
        self.cushion_gap = tk.StringVar(value="5")
        entry_cushion_gap = ttk.Entry(f_settings_row3, textvariable=self.cushion_gap, width=8, validate="key", validatecommand=(self.register(self.validate_number), "%P"))
        entry_cushion_gap.pack(side=tk.LEFT, padx=5)
        entry_cushion_gap.bind("<Return>", self.on_enter_pressed)

        f_settings_row4 = ttk.Frame(f_settings)
        f_settings_row4.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        ttk.Label(f_settings_row4, text="Przesunięcie X [mm]:").pack(side=tk.LEFT, padx=5)
        self.offset_x = tk.StringVar(value="0")
        entry_offset_x = ttk.Entry(f_settings_row4, textvariable=self.offset_x, width=8, validate="key", validatecommand=(self.register(self.validate_number), "%P"))
        entry_offset_x.pack(side=tk.LEFT, padx=5)
        entry_offset_x.bind("<Return>", self.on_enter_pressed)

        f_settings_row5 = ttk.Frame(f_settings)
        f_settings_row5.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        ttk.Label(f_settings_row5, text="Przesunięcie Y [mm]:").pack(side=tk.LEFT, padx=5)
        self.offset_y = tk.StringVar(value="0")
        entry_offset_y = ttk.Entry(f_settings_row5, textvariable=self.offset_y, width=8, validate="key", validatecommand=(self.register(self.validate_number), "%P"))
        entry_offset_y.pack(side=tk.LEFT, padx=5)
        entry_offset_y.bind("<Return>", self.on_enter_pressed)

        btn_frame = ttk.Frame(gui_frame)
        btn_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        self.btn_show = ttk.Button(btn_frame, text="Pokaż układy", command=self.show_packing)
        self.btn_show.pack(side=tk.LEFT, padx=5)

        self.btn_compare = ttk.Button(btn_frame, text="Porównaj kartony", command=self.compare_cartons)
        self.btn_compare.pack(side=tk.LEFT, padx=5)

        self.fig = plt.Figure(figsize=(12, 6))
        self.axes = self.fig.subplots(1, 3)
        self.canvas = FigureCanvasTkAgg(self.fig, master=main_frame)
        self.canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        self.carton_w.trace_add("write", self.reset_carton_choice)
        self.carton_l.trace_add("write", self.reset_carton_choice)
        self.carton_h.trace_add("write", self.reset_carton_choice)
        self.prod_h_rect.trace_add("write", self.on_prod_h_rect_changed)
        self.prod_h_circle.trace_add("write", self.on_prod_h_circle_changed)
        self.update_carton_list()
        self.update_product_fields()

    def validate_number(self, value):
        if value == "":
            return True
        value = value.replace(",", ".")
        try:
            float_value = float(value)
            return 0 <= float_value <= 10000
        except ValueError:
            return False

    def parse_dim_safe(self, var):
        try:
            value = var.get().replace(",", ".")
            float_value = float(value)
            return max(0, min(float_value, 10000))
        except (ValueError, TypeError):
            return 0

    def validate_dimensions(self, w_c, l_c, w_p=None, l_p=None, diam=None, margin=0):
        item_type = "kartonik" if self.prod_type.get() == "rectangle" else "pojemnik"
        if w_c <= 0 or l_c <= 0:
            messagebox.showwarning("Błąd", "Wymiary kartonu muszą być większe od zera.")
            return False
        if self.prod_type.get() == "rectangle":
            if w_p is None or l_p is None:
                return False
            if w_p <= 0 or l_p <= 0:
                messagebox.showwarning("Błąd", f"Wymiary {item_type}a muszą być większe od zera.")
                return False
            eff_w = w_c - margin
            eff_l = l_c - margin
            if eff_w < w_p or eff_l < l_p:
                messagebox.showwarning("Ostrzeżenie", f"Za mały karton dla podanego luzu – nie zmieści się żaden {item_type}.")
                return False
        else:
            if diam is None:
                return False
            if diam <= 0:
                messagebox.showwarning("Błąd", f"Średnica {item_type}a musi być większa od zera.")
                return False
            eff_w = w_c - margin
            eff_l = l_c - margin
            if eff_w < diam or eff_l < diam:
                messagebox.showwarning("Ostrzeżenie", f"Za mały karton dla podanego luzu – nie zmieści się żaden {item_type}.")
                return False
        return True

    def reset_carton_choice(self, *args):
        if self.updating_carton:
            return
        current_w = self.parse_dim_safe(self.carton_w)
        current_l = self.parse_dim_safe(self.carton_l)
        current_h = self.parse_dim_safe(self.carton_h)
        selected_carton = self.carton_choice.get()
        if selected_carton != "Manual":
            key = selected_carton.split()[0]
            if key in self.predefined_cartons:
                w, l, h = self.predefined_cartons[key]
                if current_w != w or current_l != l or current_h != h:
                    self.carton_choice.set("Manual")

    def draw_carton_and_margin(self, ax, width, height, margin):
        ax.add_patch(plt.Rectangle((0, 0), width, height, fill=False, edgecolor='black'))
        ax.add_patch(plt.Rectangle((0, 0), width - margin, height - margin, fill=False, edgecolor='gray', linestyle='--'))
        ax.set_xlim(0, width)
        ax.set_ylim(0, height)

    def add_air_cushions(self, ax, width, height, positions, h_c):
        if self.use_cushions.get():
            cushion_positions = place_air_cushions(width, height, positions, min_gap=self.parse_dim_safe(self.cushion_gap), offset_x=self.parse_dim_safe(self.offset_x), offset_y=self.parse_dim_safe(self.offset_y))
            for (x0, y0, ww, hh) in cushion_positions:
                ax.add_patch(plt.Rectangle((x0, y0), ww, hh, fill=True, facecolor='yellow', edgecolor='black', alpha=0.5))
            if h_c > 0 and h_c < 110:
                messagebox.showinfo("Informacja", "Sprawdź fizycznie, czy poduszka się zmieści (wysokość poduszki: 110 mm).")

    def draw_vertical(self, ax, w_c, l_c, w_p, l_p, margin, h_c):
        c_vert, pos_vert = pack_rectangles_2d(w_c, l_c, w_p, l_p, margin)
        if not pos_vert:
            return 0, [], 0, 0
        mxv, myv = 0, 0
        for (x0, y0, ww, hh) in pos_vert:
            if x0 + ww > mxv:
                mxv = x0 + ww
            if y0 + hh > myv:
                myv = y0 + hh
            ax.add_patch(plt.Rectangle((x0, y0), ww, hh, fill=False, edgecolor='blue'))
        self.draw_carton_and_margin(ax, w_c, l_c, margin)
        self.add_air_cushions(ax, w_c, l_c, pos_vert, h_c)
        return c_vert, pos_vert, mxv, myv

    def draw_horizontal(self, ax, w_c, l_c, w_p, l_p, margin, h_c):
        c_horz, pos_horz = pack_rectangles_2d(w_c, l_c, l_p, w_p, margin)
        if not pos_horz:
            return 0, [], 0, 0
        mxh, myh = 0, 0
        for (x0, y0, ww, hh) in pos_horz:
            if x0 + ww > mxh:
                mxh = x0 + ww
            if y0 + hh > myh:
                myh = y0 + hh
            ax.add_patch(plt.Rectangle((x0, y0), ww, hh, fill=False, edgecolor='blue'))
        self.draw_carton_and_margin(ax, w_c, l_c, margin)
        self.add_air_cushions(ax, w_c, l_c, pos_horz, h_c)
        return c_horz, pos_horz, mxh, myh

    def draw_mixed(self, ax, w_c, l_c, w_p, l_p, margin, h_c):
        c_mix, pos_mix = pack_rectangles_mixed_greedy(w_c, l_c, w_p, l_p, margin)
        if not pos_mix:
            return 0, [], 0, 0

        if self.maximize_mixed.get():
            c_mix, pos_mix = maximize_mixed_layout(w_c, l_c, w_p, l_p, margin, pos_mix)

        mxm, mym = 0, 0
        for (x0, y0, ww, hh) in pos_mix:
            if x0 + ww > mxm:
                mxm = x0 + ww
            if y0 + hh > mym:
                mym = y0 + hh
            ax.add_patch(plt.Rectangle((x0, y0), ww, hh, fill=False, edgecolor='blue'))
        self.draw_carton_and_margin(ax, w_c, l_c, margin)
        self.add_air_cushions(ax, w_c, l_c, pos_mix, h_c)
        return c_mix, pos_mix, mxm, mym

    def draw_grid(self, ax, w_c, l_c, diam, margin, h_c):
        grid_centers = pack_circles_grid_bottomleft(w_c, l_c, diam, margin)
        if not grid_centers:
            return 0, [], 0, 0
        r = diam / 2
        mgx, mgy = 0, 0
        grid_positions = [(cx - r, cy - r, diam, diam) for (cx, cy) in grid_centers]
        for (cx, cy) in grid_centers:
            if cx > mgx:
                mgx = cx
            if cy > mgy:
                mgy = cy
            ax.add_patch(plt.Circle((cx, cy), r, fill=False, edgecolor='blue'))
        self.draw_carton_and_margin(ax, w_c, l_c, margin)
        self.add_air_cushions(ax, w_c, l_c, grid_positions, h_c)
        return len(grid_centers), grid_positions, mgx, mgy

    def draw_hex(self, ax, w_c, l_c, diam, margin, h_c):
        hex_top = pack_hex_top_down(w_c, l_c, diam, margin)
        if not hex_top:
            return 0, [], 0, 0
        r = diam / 2
        mhx, mhy = 0, 0
        hex_positions = [(cx - r, cy - r, diam, diam) for (cx, cy) in hex_top]
        for (cx, cy) in hex_top:
            if cx > mhx:
                mhx = cx
            if cy > mhy:
                mhy = cy
            ax.add_patch(plt.Circle((cx, cy), r, fill=False, edgecolor='green'))
        self.draw_carton_and_margin(ax, w_c, l_c, margin)
        self.add_air_cushions(ax, w_c, l_c, hex_positions, h_c)
        return len(hex_top), hex_positions, mhx, mhy

    def draw_hex_rev(self, ax, w_c, l_c, diam, margin, h_c):
        hex_rev = pack_hex_bottom_up(l_c, w_c, diam, margin)
        if not hex_rev:
            return 0, [], 0, 0
        r = diam / 2
        mrx, mry = 0, 0
        hex_rev_positions = [(cx - r, cy - r, diam, diam) for (cx, cy) in hex_rev]
        for (cx, cy) in hex_rev:
            if cx > mrx:
                mrx = cx
            if cy > mry:
                mry = cy
            ax.add_patch(plt.Circle((cx, cy), r, fill=False, edgecolor='green'))
        self.draw_carton_and_margin(ax, l_c, w_c, margin)
        self.add_air_cushions(ax, l_c, w_c, hex_rev_positions, h_c)
        return len(hex_rev), hex_rev_positions, mrx, mry

    def on_prod_h_rect_changed(self, *args):
        current_h = self.prod_h_rect.get()
        if current_h != self.prev_prod_h_rect:
            self.prev_prod_h_rect = current_h
            self.update_carton_list()

    def on_prod_h_circle_changed(self, *args):
        current_h = self.prod_h_circle.get()
        if current_h != self.prev_prod_h_circle:
            self.prev_prod_h_circle = current_h
            self.update_carton_list()

    def update_carton_list(self, *args):
        prod_height = (
            self.parse_dim_safe(self.prod_h_rect)
            if self.prod_type.get() == "rectangle"
            else self.parse_dim_safe(self.prod_h_circle)
        )
        cvals = []
        for k, dims in self.predefined_cartons.items():
            w, l, h = dims
            free_space = h - prod_height if prod_height > 0 else float('inf')
            if prod_height > 0 and prod_height > h:
                label = f"{k}: {w}x{l}x{h} (Za niski)"
                cvals.append((label, float('inf')))
            else:
                label = f"{k}: {w}x{l}x{h} (luz: {free_space:.1f} mm)"
                cvals.append((label, free_space))
        cvals.sort(key=lambda x: x[1])
        cvals = ["Manual"] + [item[0] for item in cvals]
        self.cb_carton['values'] = cvals
        if self.carton_choice.get() not in cvals:
            self.carton_choice.set("Manual")

    def update_product_fields(self):
        if self.prod_type.get() == "rectangle":
            self.f_rect_container.pack(side=tk.LEFT, fill=tk.X, padx=5)
            self.f_circle_container.pack_forget()
            self.rb_rect.configure(style="Selected.TRadiobutton")
            self.rb_circle.configure(style="Unselected.TRadiobutton")
        else:
            self.f_rect_container.pack_forget()
            self.f_circle_container.pack(side=tk.LEFT, fill=tk.X, padx=5)
            self.rb_rect.configure(style="Unselected.TRadiobutton")
            self.rb_circle.configure(style="Selected.TRadiobutton")
        self.update_carton_list()
        self.show_packing()

    def on_carton_selected(self, event=None):
        try:
            self.updating_carton = True
            val = self.carton_choice.get()
            if val != "Manual":
                key = val.split(":")[0]
                if key in self.predefined_cartons:
                    w, l, h = self.predefined_cartons[key]
                    self.carton_w.set(str(w))
                    self.carton_l.set(str(l))
                    self.carton_h.set(str(h))
            self.show_packing()
        finally:
            self.updating_carton = False

    def on_enter_pressed(self, event=None):
        self.show_packing()

    def show_packing(self):
        for ax in self.axes:
            ax.clear()
            ax.set_aspect("equal")

        w_c = self.parse_dim_safe(self.carton_w)
        l_c = self.parse_dim_safe(self.carton_l)
        h_c = self.parse_dim_safe(self.carton_h)
        margin = self.parse_dim_safe(self.margin)
        eff_area = (w_c - margin) * (l_c - margin)

        if self.prod_type.get() == "rectangle":
            w_p = self.parse_dim_safe(self.prod_w)
            l_p = self.parse_dim_safe(self.prod_l)
            h_p = self.parse_dim_safe(self.prod_h_rect)
            if not self.validate_dimensions(w_c, l_c, w_p, l_p, margin=margin):
                return

            c_vert, pos_vert, mxv, myv = self.draw_vertical(self.axes[0], w_c, l_c, w_p, l_p, margin, h_c)
            c_horz, pos_horz, mxh, myh = self.draw_horizontal(self.axes[1], w_c, l_c, w_p, l_p, margin, h_c)
            c_mix, pos_mix, mxm, mym = self.draw_mixed(self.axes[2], w_c, l_c, w_p, l_p, margin, h_c)

            if not pos_vert and not pos_horz and not pos_mix:
                messagebox.showwarning("Ostrzeżenie", "Nie można zmieścić żadnego kartonika w żadnym układzie.")
                return

            if pos_vert:
                area_occupied = c_vert * w_p * l_p
                area_util = (area_occupied / eff_area) * 100 if eff_area > 0 else 0
                vol_occupied = c_vert * w_p * l_p * h_p if h_p > 0 else 0
                vol_total = w_c * l_c * h_c if h_c > 0 else float('inf')
                vol_util = (vol_occupied / vol_total) * 100 if vol_total > 0 else 0
                self.axes[0].set_title(
                    f"Pionowo: {c_vert} kartoników\n"
                    f"Wolne miejsce na prawo={w_c - mxv:.1f}\n"
                    f"Wolne miejsce do góry={l_c - myv:.1f}\n"
                    f"Zajętość pow.: {area_util:.1f}%\n"
                    f"Zajętość obj.: {vol_util:.1f}%",
                    fontsize=10
                )
            else:
                self.axes[0].set_title("Pionowo: brak możliwości", fontsize=10)

            if pos_horz:
                area_occupied = c_horz * w_p * l_p
                area_util = (area_occupied / eff_area) * 100 if eff_area > 0 else 0
                vol_occupied = c_horz * w_p * l_p * h_p if h_p > 0 else 0
                vol_total = w_c * l_c * h_c if h_c > 0 else float('inf')
                vol_util = (vol_occupied / vol_total) * 100 if vol_total > 0 else 0
                self.axes[1].set_title(
                    f"Poziomo: {c_horz} kartoników\n"
                    f"Wolne miejsce na prawo={w_c - mxh:.1f}\n"
                    f"Wolne miejsce do góry={l_c - myh:.1f}\n"
                    f"Zajętość pow.: {area_util:.1f}%\n"
                    f"Zajętość obj.: {vol_util:.1f}%",
                    fontsize=10
                )
            else:
                self.axes[1].set_title("Poziomo: brak możliwości", fontsize=10)

            if pos_mix:
                area_occupied = c_mix * w_p * l_p
                area_util = (area_occupied / eff_area) * 100 if eff_area > 0 else 0
                vol_occupied = c_mix * w_p * l_p * h_p if h_p > 0 else 0
                vol_total = w_c * l_c * h_c if h_c > 0 else float('inf')
                vol_util = (vol_occupied / vol_total) * 100 if vol_total > 0 else 0
                self.axes[2].set_title(
                    f"Mieszane: {c_mix} kartoników\n"
                    f"Wolne miejsce na prawo={w_c - mxm:.1f}\n"
                    f"Wolne miejsce do góry={l_c - mym:.1f}\n"
                    f"Zajętość pow.: {area_util:.1f}%\n"
                    f"Zajętość obj.: {vol_util:.1f}%",
                    fontsize=10
                )
            else:
                self.axes[2].set_title("Mieszane: brak możliwości", fontsize=10)

        else:
            diam = self.parse_dim_safe(self.prod_diam)
            h_p = self.parse_dim_safe(self.prod_h_circle)
            if not self.validate_dimensions(w_c, l_c, diam=diam, margin=margin):
                return

            c_grid, grid_pos, mgx, mgy = self.draw_grid(self.axes[0], w_c, l_c, diam, margin, h_c)
            c_hex, hex_pos, mhx, mhy = self.draw_hex(self.axes[1], w_c, l_c, diam, margin, h_c)
            c_rev, hex_rev_pos, mrx, mry = self.draw_hex_rev(self.axes[2], w_c, l_c, diam, margin, h_c)

            if not grid_pos and not hex_pos and not hex_rev_pos:
                messagebox.showwarning("Ostrzeżenie", "Nie można zmieścić żadnego pojemnika w żadnym układzie.")
                return

            r = diam / 2
            circle_area = math.pi * r * r

            if grid_pos:
                area_occupied = c_grid * circle_area
                area_util = (area_occupied / eff_area) * 100 if eff_area > 0 else 0
                vol_occupied = c_grid * circle_area * h_p if h_p > 0 else 0
                vol_total = w_c * l_c * h_c if h_c > 0 else float('inf')
                vol_util = (vol_occupied / vol_total) * 100 if vol_total > 0 else 0
                self.axes[0].set_title(
                    f"Siatka: {c_grid}\n"
                    f"Wolne miejsce na prawo={w_c - (mgx + r):.1f}\n"
                    f"Wolne miejsce do góry={l_c - (mgy + r):.1f}\n"
                    f"Zajętość pow.: {area_util:.1f}%\n"
                    f"Zajętość obj.: {vol_util:.1f}%",
                    fontsize=10
                )
            else:
                self.axes[0].set_title("Siatka: brak możliwości", fontsize=10)

            if hex_pos:
                area_occupied = c_hex * circle_area
                area_util = (area_occupied / eff_area) * 100 if eff_area > 0 else 0
                vol_occupied = c_hex * circle_area * h_p if h_p > 0 else 0
                vol_total = w_c * l_c * h_c if h_c > 0 else float('inf')
                vol_util = (vol_occupied / vol_total) * 100 if vol_total > 0 else 0
                self.axes[1].set_title(
                    f"Hex: {c_hex}\n"
                    f"Wolne miejsce na prawo={w_c - (mhx + r):.1f}\n"
                    f"Wolne miejsce do góry={l_c - (mhy + r):.1f}\n"
                    f"Zajętość pow.: {area_util:.1f}%\n"
                    f"Zajętość obj.: {vol_util:.1f}%",
                    fontsize=10
                )
            else:
                self.axes[1].set_title("Hex: brak możliwości", fontsize=10)

            if hex_rev_pos:
                area_occupied = c_rev * circle_area
                area_util = (area_occupied / eff_area) * 100 if eff_area > 0 else 0
                vol_occupied = c_rev * circle_area * h_p if h_p > 0 else 0
                vol_total = w_c * l_c * h_c if h_c > 0 else float('inf')
                vol_util = (vol_occupied / vol_total) * 100 if vol_total > 0 else 0
                self.axes[2].set_title(
                    f"Hex(rev): {c_rev}\n"
                    f"Wolne miejsce na prawo={l_c - (mrx + r):.1f}\n"
                    f"Wolne miejsce do góry={w_c - (mry + r):.1f}\n"
                    f"Zajętość pow.: {area_util:.1f}%\n"
                    f"Zajętość obj.: {vol_util:.1f}%",
                    fontsize=10
                )
            else:
                self.axes[2].set_title("Hex(rev): brak możliwości", fontsize=10)

        self.fig.tight_layout()
        self.canvas.draw()

    def compare_cartons(self):
        is_rectangle = self.prod_type.get() == "rectangle"
        if is_rectangle:
            w_p = self.parse_dim_safe(self.prod_w)
            l_p = self.parse_dim_safe(self.prod_l)
            h_p = self.parse_dim_safe(self.prod_h_rect)
        else:
            diam = self.parse_dim_safe(self.prod_diam)
            h_p = self.parse_dim_safe(self.prod_h_circle)

        margin = self.parse_dim_safe(self.margin)
        results = []
        for key, dims in self.predefined_cartons.items():
            w_c, l_c, h_c = dims
            if h_p > 0 and h_p > h_c:
                continue
            if is_rectangle:
                if not self.validate_dimensions(w_c, l_c, w_p, l_p, margin=margin):
                    continue
                c_vert, _ = pack_rectangles_2d(w_c, l_c, w_p, l_p, margin)
                c_horz, _ = pack_rectangles_2d(w_c, l_c, l_p, w_p, margin)
                c_mix, _ = pack_rectangles_mixed_greedy(w_c, l_c, w_p, l_p, margin)
                best_count = max(c_vert, c_horz, c_mix)
                best_layout = "Pionowo" if best_count == c_vert else "Poziomo" if best_count == c_horz else "Mieszane"
                results.append((key, w_c, l_c, h_c, c_vert, c_horz, c_mix, best_count, best_layout))
            else:
                if not self.validate_dimensions(w_c, l_c, diam=diam, margin=margin):
                    continue
                c_grid = len(pack_circles_grid_bottomleft(w_c, l_c, diam, margin))
                c_hex = len(pack_hex_top_down(w_c, l_c, diam, margin))
                c_rev = len(pack_hex_bottom_up(l_c, w_c, diam, margin))
                best_count = max(c_grid, c_hex, c_rev)
                best_layout = "Siatka" if best_count == c_grid else "Hex" if best_count == c_hex else "Hex(rev)"
                results.append((key, w_c, l_c, h_c, c_grid, c_hex, c_rev, best_count, best_layout))

        if not results:
            messagebox.showinfo("Brak wyników", "Brak odpowiednich kartonów do porównania.")
            return

        results.sort(key=lambda x: (x[7], x[4]), reverse=True)

        compare_window = tk.Toplevel(self)
        compare_window.title("Porównanie kartonów – dwuklik wybiera karton")
        layout1 = "Pionowo" if is_rectangle else "Siatka"
        layout2 = "Poziomo" if is_rectangle else "Hex"
        layout3 = "Mieszane" if is_rectangle else "Hex(rev)"
        tree = ttk.Treeview(compare_window, columns=("Karton", "Wymiary", layout1, layout2, layout3, "Najlepszy"), show="headings")
        tree.heading("Karton", text="Karton")
        tree.heading("Wymiary", text="Wymiary (mm)")
        tree.heading(layout1, text=layout1)
        tree.heading(layout2, text=layout2)
        tree.heading(layout3, text=layout3)
        tree.heading("Najlepszy", text="Najlepszy układ")
        tree.column("Karton", width=100)
        tree.column("Wymiary", width=150)
        tree.column(layout1, width=80, anchor="center")
        tree.column(layout2, width=80, anchor="center")
        tree.column(layout3, width=80, anchor="center")
        tree.column("Najlepszy", width=150)

        for key, w_c, l_c, h_c, c1, c2, c3, best_count, best_layout in results:
            tree.insert("", tk.END, values=(key, f"{w_c}x{l_c}x{h_c}", c1, c2, c3, f"{best_count} ({best_layout})"))

        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def on_tree_double_click(event):
            selection = tree.selection()
            if not selection:
                return
            values = tree.item(selection[0], "values")
            if not values:
                return
            dims = values[1].split("x")
            if len(dims) != 3:
                return
            self.carton_choice.set("Manual")
            self.carton_w.set(dims[0])
            self.carton_l.set(dims[1])
            self.carton_h.set(dims[2])
            compare_window.destroy()
            self.show_packing()

        tree.bind("<Double-1>", on_tree_double_click)

