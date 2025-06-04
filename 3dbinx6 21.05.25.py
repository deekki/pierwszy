import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk,
)
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import math
import numpy as np
from core.utils import load_cartons, load_pallets



def parse_dim(var: tk.StringVar) -> float:
    try:
        val = float(var.get().replace(",", "."))
        return max(0, val)
    except:
        messagebox.showwarning("Błąd", "Wprowadzono niepoprawną wartość. Użyto 0.")
        return 0.0


def add_box(ax, x, y, z, dx, dy, dz, color="red", alpha=0.2):
    """Draw a 3D box using Poly3DCollection."""
    verts = [
        [(x, y, z), (x + dx, y, z), (x + dx, y + dy, z), (x, y + dy, z)],
        [(x, y, z + dz), (x + dx, y, z + dz), (x + dx, y + dy, z + dz), (x, y + dy, z + dz)],
        [(x, y, z), (x + dx, y, z), (x + dx, y, z + dz), (x, y, z + dz)],
        [(x + dx, y, z), (x + dx, y + dy, z), (x + dx, y + dy, z + dz), (x + dx, y, z + dz)],
        [(x, y + dy, z), (x + dx, y + dy, z), (x + dx, y + dy, z + dz), (x, y + dy, z + dz)],
        [(x, y, z), (x, y + dy, z), (x, y + dy, z + dz), (x, y, z + dz)],
    ]
    poly = Poly3DCollection(verts, facecolors=color, edgecolors="black", alpha=alpha)
    ax.add_collection3d(poly)

def pack_rectangles_2d(width, height, wprod, lprod, margin=0):
    eff_width = width - margin
    eff_height = height - margin
    if eff_width < wprod or eff_height < lprod:
        return 0, []
    n_w = int(eff_width // wprod)
    n_h = int(eff_height // lprod)
    positions = []
    for i in range(n_w):
        for j in range(n_h):
            x0 = i * wprod
            y0 = j * lprod
            positions.append((x0, y0, wprod, lprod))
    return len(positions), positions

def pack_rectangles_mixed_greedy(width, height, wprod, lprod, margin=0):
    eff_width = width - margin
    eff_height = height - margin
    if eff_width < min(wprod, lprod) or eff_height < min(wprod, lprod):
        return 0, []
    best_count = 0
    best_positions = []
    max_cols_normal = int(eff_width // wprod)
    max_rows_normal = int(eff_height // lprod)
    for normal_cols in range(max_cols_normal + 1):
        leftover_x = eff_width - normal_cols * wprod
        if leftover_x < 0:
            continue
        rotated_cols = int(leftover_x // lprod)
        count_normal = normal_cols * int(eff_height // lprod)
        count_rot = rotated_cols * int(eff_height // wprod)
        total_c = count_normal + count_rot
        if total_c > best_count:
            best_count = total_c
            temp_positions = []
            for nc in range(normal_cols):
                for row in range(int(eff_height // lprod)):
                    temp_positions.append((nc * wprod, row * lprod, wprod, lprod))
            for rc in range(rotated_cols):
                for row in range(int(eff_height // wprod)):
                    x0 = normal_cols * wprod + rc * lprod
                    y0 = row * wprod
                    temp_positions.append((x0, y0, lprod, wprod))
            best_positions = temp_positions
    for normal_rows in range(max_rows_normal + 1):
        leftover_y = eff_height - normal_rows * lprod
        if leftover_y < 0:
            continue
        rotated_rows = int(leftover_y // wprod)
        count_normal = normal_rows * int(eff_width // wprod)
        count_rot = rotated_rows * int(eff_width // lprod)
        total_c = count_normal + count_rot
        if total_c > best_count:
            best_count = total_c
            temp_positions = []
            for nr in range(normal_rows):
                for col in range(int(eff_width // wprod)):
                    temp_positions.append((col * wprod, nr * lprod, wprod, lprod))
            for rr in range(rotated_rows):
                for col in range(int(eff_width // lprod)):
                    x0 = col * lprod
                    y0 = normal_rows * lprod + rr * wprod
                    temp_positions.append((x0, y0, lprod, wprod))
            best_positions = temp_positions
    return best_count, best_positions

def pack_rectangles_mixed_max(width, height, wprod, lprod, margin=0):
    eff_width = width - margin
    eff_height = height - margin
    if eff_width < min(wprod, lprod) or eff_height < min(wprod, lprod):
        return 0, []
    best_count = 0
    best_positions = []
    free_list = [(0, 0, eff_width, eff_height)]
    def dfs(count, positions, free_list):
        nonlocal best_count, best_positions
        if count > best_count:
            best_count = count
            best_positions = positions.copy()
        for i, rect in enumerate(free_list):
            x, y, W, H = rect
            if W >= wprod and H >= lprod:
                new_positions = positions.copy()
                new_positions.append((x, y, wprod, lprod))
                new_free = split_rect(rect, wprod, lprod)
                new_free_list = free_list[:i] + free_list[i+1:] + new_free
                dfs(count + 1, new_positions, new_free_list)
            if W >= lprod and H >= wprod:
                new_positions = positions.copy()
                new_positions.append((x, y, lprod, wprod))
                new_free = split_rect(rect, lprod, wprod)
                new_free_list = free_list[:i] + free_list[i+1:] + new_free
                dfs(count + 1, new_positions, new_free_list)
    dfs(0, [], free_list)
    return best_count, best_positions

def split_rect(rect, w, h):
    x, y, W, H = rect
    leftover = []
    if W - w > 0:
        leftover.append((x + w, y, W - w, H))
    if H - h > 0:
        leftover.append((x, y + h, w, H - h))
    return leftover

def pack_circles_grid_bottomleft(W, H, diam, margin=0):
    eff_W = W - margin
    eff_H = H - margin
    if eff_W < diam or eff_H < diam:
        return []
    r = diam / 2
    n_w = int(eff_W // diam)
    n_h = int(eff_H // diam)
    centers = []
    for i in range(n_w):
        for j in range(n_h):
            cx = i * diam + r
            cy = j * diam + r
            centers.append((cx, cy))
    return centers

def pack_hex_top_down(W, H, diam, margin=0):
    eff_W = W - margin
    eff_H = H - margin
    if eff_W < diam or eff_H < diam:
        return []
    r = diam / 2
    dy = math.sqrt(3) * r
    centers = []
    y = r
    row_idx = 0
    while y + r <= eff_H:
        if row_idx % 2 == 0:
            x_start = r
        else:
            x_start = r + diam / 2
        x = x_start
        row = []
        while x + r <= eff_W:
            row.append((x, y))
            x += diam
        centers.extend(row)
        y += dy
        row_idx += 1
    return centers

def pack_hex_bottom_up(W, H, diam, margin=0):
    eff_W = W - margin
    eff_H = H - margin
    if eff_W < diam or eff_H < diam:
        return []
    r = diam / 2
    dy = math.sqrt(3) * r
    centers = []
    y = r
    row_idx = 0
    while y + r <= eff_H:
        if row_idx % 2 == 0:
            x_start = r
        else:
            x_start = r + diam / 2
        x = x_start
        row = []
        while x + r <= eff_W:
            row.append((x, y))
            x += diam
        centers.extend(row)
        y += dy
        row_idx += 1
    return centers

def check_collision(cushion_pos, product_positions):
    cx, cy, cw, ch = cushion_pos
    for pos in product_positions:
        px, py, pw, ph = pos
        if not (cx + cw <= px or cx >= px + pw or cy + ch <= py or cy >= py + ph):
            return True
    return False

def place_air_cushions(w_c, l_c, occupied_positions, cushion_w=37, cushion_l=175, cushion_h=110, min_gap=5, offset_x=0, offset_y=0):
    positions = []
    left_x = offset_x
    right_x = w_c - cushion_w - offset_x
    top_y = l_c - cushion_w - offset_y
    bottom_y = offset_y
    count_left = int((l_c - 2 * offset_y) // (cushion_l + min_gap))
    for i in range(count_left):
        y = offset_y + i * (cushion_l + min_gap)
        pos = (left_x, y, cushion_w, cushion_l)
        if y + cushion_l <= l_c and not check_collision(pos, occupied_positions):
            positions.append(pos)
    count_right = int((l_c - 2 * offset_y) // (cushion_l + min_gap))
    for i in range(count_right):
        y = offset_y + i * (cushion_l + min_gap)
        pos = (right_x, y, cushion_w, cushion_l)
        if y + cushion_l <= l_c and not check_collision(pos, occupied_positions):
            positions.append(pos)
    count_top = int((w_c - 2 * offset_x) // (cushion_l + min_gap))
    for i in range(count_top):
        x = offset_x + i * (cushion_l + min_gap)
        pos = (x, top_y, cushion_l, cushion_w)
        if x + cushion_l <= w_c and not check_collision(pos, occupied_positions):
            positions.append(pos)
    count_bottom = int((w_c - 2 * offset_x) // (cushion_l + min_gap))
    for i in range(count_bottom):
        x = offset_x + i * (cushion_l + min_gap)
        pos = (x, bottom_y, cushion_l, cushion_w)
        if x + cushion_l <= w_c and not check_collision(pos, occupied_positions):
            positions.append(pos)
    return positions

def maximize_mixed_layout(w_c, l_c, w_p, l_p, margin, initial_positions):
    eff_w = w_c - margin
    eff_l = l_c - margin
    free_areas = [(0, 0, eff_w, eff_l)]
    occupied_positions = initial_positions.copy()
    count = len(occupied_positions)

    for pos in initial_positions:
        x, y, w, h = pos
        new_free = []
        for fx, fy, fw, fh in free_areas:
            if x + w <= fx or x >= fx + fw or y + h <= fy or y >= fy + fh:
                new_free.append((fx, fy, fw, fh))
            else:
                if x > fx:
                    new_free.append((fx, fy, x - fx, fh))
                if x + w < fx + fw:
                    new_free.append((x + w, fy, fx + fw - (x + w), fh))
                if y > fy:
                    new_free.append((fx, fy, fw, y - fy))
                if y + h < fy + fh:
                    new_free.append((fx, y + h, fw, fy + fh - (y + h)))
        free_areas = new_free

    while free_areas:
        free_areas.sort(key=lambda x: x[2] * x[3], reverse=True)
        fx, fy, fw, fh = free_areas.pop(0)
        placed = False

        if fw >= w_p and fh >= l_p:
            occupied_positions.append((fx, fy, w_p, l_p))
            count += 1
            new_free = []
            for afx, afy, afw, afh in free_areas:
                if fx + w_p <= afx or fx >= afx + afw or fy + l_p <= afy or fy >= afy + afh:
                    new_free.append((afx, afy, afw, afh))
                else:
                    if fx > afx:
                        new_free.append((afx, afy, fx - afx, afh))
                    if fx + w_p < afx + afw:
                        new_free.append((fx + w_p, afy, afx + afw - (fx + w_p), afh))
                    if fy > afy:
                        new_free.append((afx, afy, afw, fy - afy))
                    if fy + l_p < afy + afh:
                        new_free.append((afx, fy + l_p, afw, afy + afh - (fy + l_p)))
            free_areas = new_free
            if fx + w_p < eff_w:
                free_areas.append((fx + w_p, fy, eff_w - (fx + w_p), l_p))
            if fy + l_p < eff_l:
                free_areas.append((fx, fy + l_p, w_p, eff_l - (fy + l_p)))
            placed = True

        if not placed and fw >= l_p and fh >= w_p:
            occupied_positions.append((fx, fy, l_p, w_p))
            count += 1
            new_free = []
            for afx, afy, afw, afh in free_areas:
                if fx + l_p <= afx or fx >= afx + afw or fy + w_p <= afy or fy >= afy + afh:
                    new_free.append((afx, afy, afw, afh))
                else:
                    if fx > afx:
                        new_free.append((afx, afy, fx - afx, afh))
                    if fx + l_p < afx + afw:
                        new_free.append((fx + l_p, afy, afx + afw - (fx + l_p), afh))
                    if fy > afy:
                        new_free.append((afx, afy, afw, fy - afy))
                    if fy + w_p < afy + afh:
                        new_free.append((afx, fy + w_p, afw, afy + afh - (fy + w_p)))
            free_areas = new_free
            if fx + l_p < eff_w:
                free_areas.append((fx + l_p, fy, eff_w - (fx + l_p), w_p))
            if fy + w_p < eff_l:
                free_areas.append((fx, fy + w_p, l_p, eff_l - (fy + w_p)))
            placed = True

        if not placed:
            continue

    return count, occupied_positions

class TabPacking2D(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
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
        self.rb_rect = ttk.Radiobutton(f_type, text="Kartoniki", variable=self.prod_type, value="rectangle", command=self.update_product_fields)
        self.rb_rect.pack(side=tk.LEFT, padx=5)
        self.rb_circle = ttk.Radiobutton(f_type, text="Pojemniki/Butelki", variable=self.prod_type, value="circle", command=self.update_product_fields)
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
            cartons = load_cartons()
            if key in cartons:
                w, l, h = cartons[key]
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
        prod_height = self.parse_dim_safe(self.prod_h_rect) if self.prod_type.get() == "rectangle" else self.parse_dim_safe(self.prod_h_circle)
        cvals = []
        cartons = load_cartons()
        for k, dims in cartons.items():
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
        else:
            self.f_rect_container.pack_forget()
            self.f_circle_container.pack(side=tk.LEFT, fill=tk.X, padx=5)
        self.update_carton_list()
        self.show_packing()

    def on_carton_selected(self, event=None):
        try:
            self.updating_carton = True
            val = self.carton_choice.get()
            if val != "Manual":
                key = val.split(":")[0]
                cartons = load_cartons()
                if key in cartons:
                    w, l, h = cartons[key]
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
        cartons = load_cartons()
        for key, dims in cartons.items():
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

class TabBox3D(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.build_ui()

    def build_ui(self):
        fr = ttk.Frame(self)
        fr.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Label(fr, text="Wymiary produktu (W, L, H) [mm]:").grid(row=0, column=0, sticky="w")
        self.prod_w = tk.DoubleVar(value=50)
        self.prod_l = tk.DoubleVar(value=50)
        self.prod_h = tk.DoubleVar(value=20)
        ttk.Entry(fr, textvariable=self.prod_w, width=8).grid(row=0, column=1, padx=5)
        ttk.Entry(fr, textvariable=self.prod_l, width=8).grid(row=0, column=2, padx=5)
        ttk.Entry(fr, textvariable=self.prod_h, width=8).grid(row=0, column=3, padx=5)

        ttk.Label(fr, text="Ilość opakowań w kartonie:").grid(row=1, column=0, sticky="w")
        self.num_units = tk.IntVar(value=20)
        ttk.Entry(fr, textvariable=self.num_units, width=8).grid(row=1, column=1, padx=5)

        self.btn_search = ttk.Button(fr, text="Znajdź najlepsze kartony", command=self.search_best_boxes)
        self.btn_search.grid(row=2, column=0, padx=5, pady=5, sticky="w")

        self.btn_opt = ttk.Button(fr, text="Optymalizuj (losowo)", command=self.optimize_box_random)
        self.btn_opt.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        self.listbox = tk.Listbox(self, width=80, height=15)
        self.listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

    def search_best_boxes(self):
        self.listbox.delete(0, tk.END)
        w_ = self.prod_w.get()
        l_ = self.prod_l.get()
        h_ = self.prod_h.get()
        units = self.num_units.get()
        product_volume = w_ * l_ * h_
        results = []
        cartons = load_cartons()
        for key, dims in cartons.items():
            bw, bl, bh = dims
            bw_ext, bl_ext, bh_ext = bw + 3, bl + 3, bh + 6
            layers = int(bh_ext // h_)
            base_count = int(bw_ext // w_) * int(bl_ext // l_)
            total_cnt = base_count * layers
            box_vol = bw_ext * bl_ext * bh_ext
            util = (total_cnt * product_volume) / box_vol if box_vol > 0 else 0
            results.append((key, bw_ext, bl_ext, bh_ext, total_cnt, util))
        results.sort(key=lambda x: (x[5], x[4]), reverse=True)
        for r in results[:10]:
            key, bw_ext, bl_ext, bh_ext, cnt, ut = r
            msg = f"{key}: {int(bw_ext)}x{int(bl_ext)}x{int(bh_ext)} mm | szt={cnt} | użycie={ut*100:.1f}%"
            self.listbox.insert(tk.END, msg)

    def optimize_box_random(self):
        self.listbox.delete(0, tk.END)
        w_ = self.prod_w.get()
        l_ = self.prod_l.get()
        h_ = self.prod_h.get()
        units = self.num_units.get()
        best_dims, best_score = random_box_optimizer_3d(w_, l_, h_, units)
        if best_dims is None:
            messagebox.showinfo("Wynik", "Nie znaleziono rozwiązania.")
        else:
            wopt, lopt, hopt = best_dims
            msg = f"Najlepsze wymiary (losowo):\n{wopt:.1f} x {lopt:.1f} x {hopt:.1f} mm\nDopasowanie: {best_score*100:.1f}%"
            messagebox.showinfo("Optymalizacja 3D", msg)

def random_box_optimizer_3d(prod_w, prod_l, prod_h, units):
    best_dims = None
    best_score = 0
    target_volume = prod_w * prod_l * prod_h * units
    for _ in range(200):
        w_ = np.random.uniform(prod_w, prod_w * 5)
        l_ = np.random.uniform(prod_l, prod_l * 5)
        h_ = np.random.uniform(prod_h, prod_h * 5)
        vol = w_ * l_ * h_
        ratio = min(vol, target_volume) / max(vol, target_volume)
        if ratio > best_score:
            best_score = ratio
            best_dims = (w_, l_, h_)
    return best_dims, best_score

class TabPallet(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill=tk.BOTH, expand=True)
        self.layouts = []
        self.current_layout_idx = 0
        self.layers = []
        self.transformations = []
        self.transform_vars = []
        self.build_ui()

    def build_ui(self):
        pallet_frame = ttk.LabelFrame(self, text="Parametry palety")
        pallet_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(pallet_frame, text="Paleta:").grid(row=0, column=0, padx=5, pady=5)
        pallets = load_pallets()
        self.pallet_var = tk.StringVar(value=pallets[0]["name"])
        pallet_menu = ttk.OptionMenu(
            pallet_frame,
            self.pallet_var,
            pallets[0]["name"],
            *[p["name"] for p in pallets],
            command=self.on_pallet_selected,
        )
        pallet_menu.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(pallet_frame, text="W (mm):").grid(row=0, column=2, padx=5, pady=5)
        self.pallet_w_var = tk.StringVar(value=str(pallets[0]["w"]))
        ttk.Entry(pallet_frame, textvariable=self.pallet_w_var, width=10).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(pallet_frame, text="L (mm):").grid(row=0, column=4, padx=5, pady=5)
        self.pallet_l_var = tk.StringVar(value=str(pallets[0]["l"]))
        ttk.Entry(pallet_frame, textvariable=self.pallet_l_var, width=10).grid(row=0, column=5, padx=5, pady=5)

        ttk.Label(pallet_frame, text="H (mm):").grid(row=0, column=6, padx=5, pady=5)
        self.pallet_h_var = tk.StringVar(value=str(pallets[0]["h"]))
        ttk.Entry(pallet_frame, textvariable=self.pallet_h_var, width=10).grid(row=0, column=7, padx=5, pady=5)

        carton_frame = ttk.LabelFrame(self, text="Parametry kartonu")
        carton_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(carton_frame, text="Karton:").grid(row=0, column=0, padx=5, pady=5)
        cartons = load_cartons()
        self.carton_var = tk.StringVar(value=list(cartons.keys())[0])
        carton_menu = ttk.OptionMenu(
            carton_frame,
            self.carton_var,
            list(cartons.keys())[0],
            *cartons.keys(),
            command=self.on_carton_selected,
        )
        carton_menu.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(carton_frame, text="W (mm):").grid(row=0, column=2, padx=5, pady=5)
        self.box_w_var = tk.StringVar(value=str(cartons[list(cartons.keys())[0]][0]))
        ttk.Entry(carton_frame, textvariable=self.box_w_var, width=10).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(carton_frame, text="L (mm):").grid(row=0, column=4, padx=5, pady=5)
        self.box_l_var = tk.StringVar(value=str(cartons[list(cartons.keys())[0]][1]))
        ttk.Entry(carton_frame, textvariable=self.box_l_var, width=10).grid(row=0, column=5, padx=5, pady=5)

        ttk.Label(carton_frame, text="H (mm):").grid(row=0, column=6, padx=5, pady=5)
        self.box_h_var = tk.StringVar(value=str(cartons[list(cartons.keys())[0]][2]))
        ttk.Entry(carton_frame, textvariable=self.box_h_var, width=10).grid(row=0, column=7, padx=5, pady=5)

        ttk.Label(carton_frame, text="Grubość tektury (mm):").grid(row=1, column=0, padx=5, pady=5)
        self.cardboard_thickness_var = tk.StringVar(value="3")
        ttk.Entry(carton_frame, textvariable=self.cardboard_thickness_var, width=10, validate="key",
                  validatecommand=(self.register(self.validate_number), "%P")).grid(row=1, column=1, padx=5, pady=5)

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
        ttk.Entry(layers_frame, textvariable=self.num_layers_var, width=5).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(layers_frame, text="Centrowanie:").grid(row=0, column=2, padx=5, pady=5)
        self.center_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(layers_frame, variable=self.center_var, command=self.compute_pallet).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(layers_frame, text="Tryb:").grid(row=0, column=4, padx=5, pady=5)
        self.center_mode_var = tk.StringVar(value="Cała warstwa")
        ttk.OptionMenu(layers_frame, self.center_mode_var, "Cała warstwa", "Cała warstwa", "Poszczególne obszary").grid(row=0, column=5, padx=5, pady=5)

        self.alternate_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(layers_frame, text="Naprzemienne transformacje", variable=self.alternate_var, command=self.update_transformations).grid(row=0, column=6, padx=5, pady=5)

        self.transform_frame = ttk.Frame(layers_frame)
        self.transform_frame.grid(row=1, column=0, columnspan=7, padx=5, pady=5)

        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(control_frame, text="Oblicz", command=self.compute_pallet).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Poprzedni", command=self.prev_layout).pack(side=tk.LEFT, padx=5)
        self.layout_label = ttk.Label(control_frame, text="Układ 1")
        self.layout_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Następny", command=self.next_layout).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Pokaż w 3D", command=self.show_3d).pack(side=tk.LEFT, padx=5)

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
        options = ["Brak", "Odbicie w poziomie", "Odbicie w pionie"]
        for i in range(int(parse_dim(self.num_layers_var))):
            ttk.Label(self.transform_frame, text=f"Warstwa {i+1}:").grid(row=i, column=0, padx=5, pady=2)
            var = tk.StringVar(value=options[0])
            ttk.OptionMenu(self.transform_frame, var, options[0], *options, command=self.update_transformations).grid(row=i, column=1, padx=5, pady=2)
            self.transform_vars.append(var)

    def on_pallet_selected(self, *args):
        pallets = load_pallets()
        selected_pallet = next(p for p in pallets if p["name"] == self.pallet_var.get())
        self.pallet_w_var.set(str(selected_pallet["w"]))
        self.pallet_l_var.set(str(selected_pallet["l"]))
        self.pallet_h_var.set(str(selected_pallet["h"]))
        self.compute_pallet()

    def on_carton_selected(self, *args):
        cartons = load_cartons()
        dims = cartons[self.carton_var.get()]
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
            elif transform == "Odbicie w poziomie":
                new_x = pallet_w - x - w
                new_y = y
                new_positions.append((new_x, new_y, w, h))
            elif transform == "Odbicie w pionie":
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
        num_layers = int(parse_dim(self.num_layers_var))

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

        # Draw pallet base with a proper height instead of a fixed value.
        add_box(ax_3d, 0, 0, 0, pallet_w, pallet_l, pallet_h, color="red", alpha=0.2)
        for layer_idx, positions in enumerate(self.layers):
            transformed = self.apply_transformation(positions, self.transformations[layer_idx], pallet_w, pallet_l, box_w_ext, box_l_ext)
            color = plt.cm.tab10(layer_idx % 10)
            for x, y, w, h in transformed:
                add_box(ax_3d, x, y, layer_idx * box_h_ext, w, h, box_h_ext, color=color, alpha=0.7)

        ax_3d.set_xlim(0, pallet_w)
        ax_3d.set_ylim(0, pallet_l)
        ax_3d.set_zlim(0, pallet_h)
        ax_3d.set_xlabel('W (mm)')
        ax_3d.set_ylabel('L (mm)')
        ax_3d.set_zlabel('H (mm)')
        canvas_3d.draw()

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Optymalizacja pakowania")
        self.geometry("1200x800")

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True)

        tab1 = TabPacking2D(notebook)
        tab2 = TabBox3D(notebook)
        tab3 = TabPallet(notebook)

        notebook.add(tab1, text="Pakowanie 2D")
        notebook.add(tab2, text="Pakowanie 3D")
        notebook.add(tab3, text="Paletyzacja")

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
