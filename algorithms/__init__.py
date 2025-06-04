from __future__ import annotations

from typing import List, Tuple
from core.models import Carton

__all__ = [
    "pack_rectangles_2d",
    "pack_rectangles_mixed_greedy",
    "pack_circles_grid_bottomleft",
    "pack_hex_top_down",
    "pack_hex_bottom_up",
    "maximize_mixed_layout",
    "place_air_cushions",
    "random_box_optimizer_3d",
]


def pack_rectangles_2d(carton: Carton, prod_w: float, prod_l: float, margin: float = 0) -> tuple[int, List[Tuple[float, float, float, float]]]:
    width, height = carton.width, carton.length
    eff_width = width - margin
    eff_height = height - margin
    if eff_width < prod_w or eff_height < prod_l:
        return 0, []
    n_w = int(eff_width // prod_w)
    n_h = int(eff_height // prod_l)
    positions: List[Tuple[float, float, float, float]] = []
    for i in range(n_w):
        for j in range(n_h):
            x0 = i * prod_w
            y0 = j * prod_l
            positions.append((x0, y0, prod_w, prod_l))
    return len(positions), positions


def pack_rectangles_mixed_greedy(carton: Carton, prod_w: float, prod_l: float, margin: float = 0) -> tuple[int, List[Tuple[float, float, float, float]]]:
    width, height = carton.width, carton.length
    eff_width = width - margin
    eff_height = height - margin
    if eff_width < min(prod_w, prod_l) or eff_height < min(prod_w, prod_l):
        return 0, []
    best_count = 0
    best_positions: List[Tuple[float, float, float, float]] = []
    max_cols_normal = int(eff_width // prod_w)
    max_rows_normal = int(eff_height // prod_l)
    for normal_cols in range(max_cols_normal + 1):
        leftover_x = eff_width - normal_cols * prod_w
        if leftover_x < 0:
            continue
        rotated_cols = int(leftover_x // prod_l)
        count_normal = normal_cols * int(eff_height // prod_l)
        count_rot = rotated_cols * int(eff_height // prod_w)
        total_c = count_normal + count_rot
        if total_c > best_count:
            best_count = total_c
            temp_positions: List[Tuple[float, float, float, float]] = []
            for nc in range(normal_cols):
                for row in range(int(eff_height // prod_l)):
                    temp_positions.append((nc * prod_w, row * prod_l, prod_w, prod_l))
            for rc in range(rotated_cols):
                for row in range(int(eff_height // prod_w)):
                    x0 = normal_cols * prod_w + rc * prod_l
                    y0 = row * prod_w
                    temp_positions.append((x0, y0, prod_l, prod_w))
            best_positions = temp_positions
    for normal_rows in range(max_rows_normal + 1):
        leftover_y = eff_height - normal_rows * prod_l
        if leftover_y < 0:
            continue
        rotated_rows = int(leftover_y // prod_w)
        count_normal = normal_rows * int(eff_width // prod_w)
        count_rot = rotated_rows * int(eff_width // prod_l)
        total_c = count_normal + count_rot
        if total_c > best_count:
            best_count = total_c
            temp_positions = []
            for nr in range(normal_rows):
                for col in range(int(eff_width // prod_w)):
                    temp_positions.append((col * prod_w, nr * prod_l, prod_w, prod_l))
            for rr in range(rotated_rows):
                for col in range(int(eff_width // prod_l)):
                    x0 = col * prod_l
                    y0 = normal_rows * prod_l + rr * prod_w
                    temp_positions.append((x0, y0, prod_l, prod_w))
            best_positions = temp_positions
    return best_count, best_positions


def split_rect(rect: Tuple[float, float, float, float], w: float, h: float) -> List[Tuple[float, float, float, float]]:
    x, y, W, H = rect
    leftover = []
    if W - w > 0:
        leftover.append((x + w, y, W - w, H))
    if H - h > 0:
        leftover.append((x, y + h, w, H - h))
    return leftover


def maximize_mixed_layout(carton: Carton, prod_w: float, prod_l: float, margin: float, initial_positions: List[Tuple[float, float, float, float]]) -> tuple[int, List[Tuple[float, float, float, float]]]:
    eff_w = carton.width - margin
    eff_l = carton.length - margin
    free_areas: List[Tuple[float, float, float, float]] = [(0, 0, eff_w, eff_l)]
    occupied_positions = initial_positions.copy()
    count = len(occupied_positions)

    for pos in initial_positions:
        x, y, w, h = pos
        new_free: List[Tuple[float, float, float, float]] = []
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

        if fw >= prod_w and fh >= prod_l:
            occupied_positions.append((fx, fy, prod_w, prod_l))
            count += 1
            new_free: List[Tuple[float, float, float, float]] = []
            for afx, afy, afw, afh in free_areas:
                if fx + prod_w <= afx or fx >= afx + afw or fy + prod_l <= afy or fy >= afy + afh:
                    new_free.append((afx, afy, afw, afh))
                else:
                    if fx > afx:
                        new_free.append((afx, afy, fx - afx, afh))
                    if fx + prod_w < afx + afw:
                        new_free.append((fx + prod_w, afy, afx + afw - (fx + prod_w), afh))
                    if fy > afy:
                        new_free.append((afx, afy, afw, fy - afy))
                    if fy + prod_l < afy + afh:
                        new_free.append((afx, fy + prod_l, afw, afy + afh - (fy + prod_l)))
            free_areas = new_free
            if fx + prod_w < eff_w:
                free_areas.append((fx + prod_w, fy, eff_w - (fx + prod_w), prod_l))
            if fy + prod_l < eff_l:
                free_areas.append((fx, fy + prod_l, prod_w, eff_l - (fy + prod_l)))
            placed = True

        if not placed and fw >= prod_l and fh >= prod_w:
            occupied_positions.append((fx, fy, prod_l, prod_w))
            count += 1
            new_free = []
            for afx, afy, afw, afh in free_areas:
                if fx + prod_l <= afx or fx >= afx + afw or fy + prod_w <= afy or fy >= afy + afh:
                    new_free.append((afx, afy, afw, afh))
                else:
                    if fx > afx:
                        new_free.append((afx, afy, fx - afx, afh))
                    if fx + prod_l < afx + afw:
                        new_free.append((fx + prod_l, afy, afx + afw - (fx + prod_l), afh))
                    if fy > afy:
                        new_free.append((afx, afy, afw, fy - afy))
                    if fy + prod_w < afy + afh:
                        new_free.append((afx, fy + prod_w, afw, afy + afh - (fy + prod_w)))
            free_areas = new_free
            if fx + prod_l < eff_w:
                free_areas.append((fx + prod_l, fy, eff_w - (fx + prod_l), prod_w))
            if fy + prod_w < eff_l:
                free_areas.append((fx, fy + prod_w, prod_l, eff_l - (fy + prod_w)))
            placed = True

        if not placed:
            continue
    return count, occupied_positions


def pack_circles_grid_bottomleft(carton: Carton, diam: float, margin: float = 0) -> List[Tuple[float, float]]:
    eff_W = carton.width - margin
    eff_H = carton.length - margin
    if eff_W < diam or eff_H < diam:
        return []
    r = diam / 2
    n_w = int(eff_W // diam)
    n_h = int(eff_H // diam)
    centers: List[Tuple[float, float]] = []
    for i in range(n_w):
        for j in range(n_h):
            cx = i * diam + r
            cy = j * diam + r
            centers.append((cx, cy))
    return centers


def pack_hex_top_down(carton: Carton, diam: float, margin: float = 0) -> List[Tuple[float, float]]:
    eff_W = carton.width - margin
    eff_H = carton.length - margin
    if eff_W < diam or eff_H < diam:
        return []
    r = diam / 2
    dy = math.sqrt(3) * r
    centers: List[Tuple[float, float]] = []
    y = r
    row_idx = 0
    while y + r <= eff_H:
        x_start = r if row_idx % 2 == 0 else r + diam / 2
        x = x_start
        row = []
        while x + r <= eff_W:
            row.append((x, y))
            x += diam
        centers.extend(row)
        y += dy
        row_idx += 1
    return centers


def pack_hex_bottom_up(carton: Carton, diam: float, margin: float = 0) -> List[Tuple[float, float]]:
    eff_W = carton.width - margin
    eff_H = carton.length - margin
    if eff_W < diam or eff_H < diam:
        return []
    r = diam / 2
    dy = math.sqrt(3) * r
    centers: List[Tuple[float, float]] = []
    y = r
    row_idx = 0
    while y + r <= eff_H:
        x_start = r if row_idx % 2 == 0 else r + diam / 2
        x = x_start
        row = []
        while x + r <= eff_W:
            row.append((x, y))
            x += diam
        centers.extend(row)
        y += dy
        row_idx += 1
    return centers


def check_collision(cushion_pos: Tuple[float, float, float, float], product_positions: List[Tuple[float, float, float, float]]) -> bool:
    cx, cy, cw, ch = cushion_pos
    for pos in product_positions:
        px, py, pw, ph = pos
        if not (cx + cw <= px or cx >= px + pw or cy + ch <= py or cy >= py + ph):
            return True
    return False


def place_air_cushions(carton: Carton, occupied_positions: List[Tuple[float, float, float, float]], cushion_w: float = 37, cushion_l: float = 175, cushion_h: float = 110, min_gap: float = 5, offset_x: float = 0, offset_y: float = 0) -> List[Tuple[float, float, float, float]]:
    w_c, l_c = carton.width, carton.length
    positions: List[Tuple[float, float, float, float]] = []
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


def random_box_optimizer_3d(prod_w: float, prod_l: float, prod_h: float, units: int) -> tuple[Carton | None, float]:
    best_dims: Carton | None = None
    best_score = 0.0
    target_volume = prod_w * prod_l * prod_h * units
    for _ in range(200):
        w_ = float(np.random.uniform(prod_w, prod_w * 5))
        l_ = float(np.random.uniform(prod_l, prod_l * 5))
        h_ = float(np.random.uniform(prod_h, prod_h * 5))
        vol = w_ * l_ * h_
        ratio = min(vol, target_volume) / max(vol, target_volume)
        if ratio > best_score:
            best_score = ratio
            best_dims = Carton(w_, l_, h_)
    return best_dims, best_score
