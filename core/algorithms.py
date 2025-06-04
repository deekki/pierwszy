import xml.etree.ElementTree as ET
from typing import List, Tuple


def pack_rectangles_mixed_greedy(width: float, height: float, wprod: float, lprod: float, margin: float = 0) -> Tuple[int, List[Tuple[float, float, float, float]]]:
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


def generate_layout_variants(pallet_w: float, pallet_l: float, box_w: float, box_l: float, margin: float = 0):
    variants = []
    count, pos = pack_rectangles_mixed_greedy(pallet_w, pallet_l, box_w, box_l, margin)
    variants.append(("Standardowy", count, pos))

    count_r, pos_r = pack_rectangles_mixed_greedy(pallet_w, pallet_l, box_l, box_w, margin)
    variants.append(("Obrócony", count_r, pos_r))

    mirror_x = [(pallet_w - x - w, y, w, h) for x, y, w, h in pos]
    variants.append(("Odbicie X", count, mirror_x))

    mirror_y = [(x, pallet_l - y - h, w, h) for x, y, w, h in pos]
    variants.append(("Odbicie Y", count, mirror_y))

    return variants


def load_pallets_from_xml(path: str):
    pallets = []
    try:
        tree = ET.parse(path)
    except Exception:
        return pallets
    root = tree.getroot()
    for p in root.findall('Pallet'):
        try:
            pallets.append({
                'name': p.get('name'),
                'w': float(p.get('w')),
                'l': float(p.get('l')),
                'h': float(p.get('h')),
                'NormHeight': float(p.get('NormHeight', 0)),
                'mass': float(p.get('mass', 0)),
            })
        except Exception:
            continue
    return pallets
