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
    if not ((w_p <= eff_w and l_p <= eff_l) or (l_p <= eff_w and w_p <= eff_l)):
        return 0, []
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
            remaining_w = fw - w_p
            remaining_h = fh - l_p
            if remaining_w > 0:
                free_areas.append((fx + w_p, fy, remaining_w, fh))
            if remaining_h > 0:
                free_areas.append((fx, fy + l_p, w_p, remaining_h))
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
            remaining_w = fw - l_p
            remaining_h = fh - w_p
            if remaining_w > 0:
                free_areas.append((fx + l_p, fy, remaining_w, fh))
            if remaining_h > 0:
                free_areas.append((fx, fy + w_p, l_p, remaining_h))
            placed = True

        if not placed:
            continue

    unique_positions = []
    seen = set()
    for pos in occupied_positions:
        if pos not in seen:
            unique_positions.append(pos)
            seen.add(pos)

    return len(unique_positions), unique_positions
