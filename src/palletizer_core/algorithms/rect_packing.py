import math

from .void_fill import maximize_mixed_layout


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



def pack_rectangles_row_by_row(width, height, wprod, lprod, margin=0):
    """Alternate carton orientation on each row.

    The algorithm fills consecutive rows starting at the bottom of the pallet.
    Odd rows use the natural carton orientation while even rows are rotated by
    90 degrees.  Boxes are packed as tightly as possible in each row without
    optimisation for remaining space.
    """
    eff_width = width - margin
    eff_height = height - margin
    positions = []
    y = 0.0
    row_idx = 0
    while True:
        if row_idx % 2 == 0:
            row_h = lprod
            col_w = wprod
        else:
            row_h = wprod
            col_w = lprod
        if y + row_h > eff_height or col_w <= 0 or row_h <= 0:
            break
        n_cols = int(eff_width // col_w)
        for c in range(n_cols):
            x = c * col_w
            positions.append((x, y, col_w, row_h))
        y += row_h
        row_idx += 1

    return len(positions), positions



def pack_pinwheel(width, height, wprod, lprod, margin=0):
    """Pack cartons in repeating 2x2 pinwheel blocks.

    Any leftover space around the regular pinwheel grid is filled using the
    mixed greedy algorithm so that cartons never overlap and remain inside the
    pallet bounds.
    """

    eff_width = width - margin
    eff_height = height - margin
    block_w = wprod + lprod
    block_h = wprod + lprod

    # If a single pinwheel block does not fit, fall back to the mixed layout
    if eff_width < block_w or eff_height < block_h:
        return pack_rectangles_mixed_greedy(eff_width, eff_height, wprod, lprod)

    n_x = int(eff_width // block_w)
    n_y = int(eff_height // block_h)
    positions = []
    for ix in range(n_x):
        for iy in range(n_y):
            x0 = ix * block_w
            y0 = iy * block_h
            positions.append((x0, y0, wprod, lprod))
            positions.append((x0 + wprod, y0, lprod, wprod))
            positions.append((x0 + lprod, y0 + wprod, wprod, lprod))
            positions.append((x0, y0 + lprod, lprod, wprod))

    leftover_x = eff_width - n_x * block_w
    leftover_y = eff_height - n_y * block_h

    # Fill the vertical strip on the right
    if leftover_x > 0:
        _, right_strip = pack_rectangles_mixed_max(
            leftover_x, eff_height, wprod, lprod
        )
        positions.extend((n_x * block_w + x, y, w, h) for x, y, w, h in right_strip)

    # Fill the horizontal strip at the top (excluding the right strip area)
    if leftover_y > 0 and n_x * block_w > 0:
        _, top_strip = pack_rectangles_mixed_max(
            n_x * block_w, leftover_y, wprod, lprod
        )
        positions.extend((x, n_y * block_h + y, w, h) for x, y, w, h in top_strip)

    return len(positions), positions



def pack_rectangles_mixed_max(width, height, wprod, lprod, margin=0):
    """Search for dense mixed layouts without exhaustive DFS."""

    eff_width = width - margin
    eff_height = height - margin
    if eff_width < min(wprod, lprod) or eff_height < min(wprod, lprod):
        return 0, []

    box_area = wprod * lprod
    orientations = [(wprod, lprod)]
    if abs(wprod - lprod) > 1e-9:
        orientations.append((lprod, wprod))

    best_count = 0
    best_positions = []

    max_nodes = 5000
    nodes_explored = 0
    stack = [(0, [], [(0.0, 0.0, eff_width, eff_height)])]

    def _split(rect, w, h):
        x, y, W, H = rect
        pieces = []
        if W - w > 1e-9:
            pieces.append((x + w, y, W - w, H))
        if H - h > 1e-9:
            pieces.append((x, y + h, w, H - h))
        return pieces

    def _prune(free_rects):
        pruned = []
        for fx, fy, fw, fh in free_rects:
            fits = False
            for ow, oh in orientations:
                if fw + 1e-9 >= ow and fh + 1e-9 >= oh:
                    fits = True
                    break
            if fits:
                pruned.append((fx, fy, fw, fh))
        return pruned

    while stack and nodes_explored < max_nodes:
        count, positions, free_rects = stack.pop()
        nodes_explored += 1

        if count > best_count:
            best_count = count
            best_positions = positions

        free_area = sum(fw * fh for _, _, fw, fh in free_rects)
        potential = count + int(free_area // box_area)
        if potential <= best_count:
            continue

        if not free_rects:
            continue

        idx = max(range(len(free_rects)), key=lambda i: free_rects[i][2] * free_rects[i][3])
        base_rect = free_rects[idx]
        remaining = free_rects[:idx] + free_rects[idx + 1 :]

        placed_any = False
        for ow, oh in orientations:
            if base_rect[2] + 1e-9 < ow or base_rect[3] + 1e-9 < oh:
                continue
            new_pos = positions + [(base_rect[0], base_rect[1], ow, oh)]
            new_free = remaining + _split(base_rect, ow, oh)
            new_free = _prune(new_free)
            stack.append((count + 1, new_pos, new_free))
            placed_any = True

        if not placed_any:
            filtered = _prune(remaining)
            if len(filtered) != len(remaining):
                remaining = filtered
            if remaining:
                stack.append((count, positions, remaining))

    ordered = sorted(best_positions, key=lambda item: (item[1], item[0]))
    return best_count, ordered


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


def pack_rectangles_dynamic(width, height, wprod, lprod, margin=0):
    """Pack rectangles using a dynamic optimisation strategy.

    The routine relies on ``rectpack`` to explore many packing permutations with
    automatic rectangle rotation. The number of cartons is not predetermined;
    instead an upper bound is estimated from the available area and every box is
    submitted to the packer. The resulting list contains only the cartons that
    successfully fit inside the pallet area without overlapping. When
    ``rectpack`` is not installed the function falls back to the bounded mixed
    search used by :func:`maximize_mixed_layout`.
    """

    try:
        from rectpack import newPacker
    except ImportError:
        count, positions = maximize_mixed_layout(width, height, wprod, lprod, margin, [])
        return count, positions

    eff_w = width - margin
    eff_h = height - margin

    if eff_w <= 0 or eff_h <= 0:
        return 0, []

    packer = newPacker(rotation=True)

    estimate = int((eff_w * eff_h) // (wprod * lprod)) + 5
    for i in range(estimate):
        packer.add_rect(wprod, lprod, i)

    packer.add_bin(eff_w, eff_h)
    packer.pack()

    positions = [(x, y, w, h) for (_, x, y, w, h, _) in packer.rect_list()]

    return len(positions), positions


def pack_rectangles_dynamic_variants(carton, pallet):
    """Generate deterministic dynamic variants using rectpack strategies."""
    width = pallet.width
    height = pallet.length
    wprod = carton.width
    lprod = carton.length

    variants = {}
    _, base = pack_rectangles_dynamic(width, height, wprod, lprod)
    variants["dynamic_default"] = base
    if abs(wprod - lprod) > 1e-6:
        _, rotated = pack_rectangles_dynamic(width, height, lprod, wprod)
        variants["dynamic_rotated"] = rotated

    try:
        from rectpack import newPacker
        from rectpack import SORT_AREA, SORT_LSIDE, SORT_PERI, SORT_SSIDE
    except ImportError:
        return variants

    sort_algos = {
        "dynamic_area": SORT_AREA,
        "dynamic_perimeter": SORT_PERI,
        "dynamic_short_side": SORT_SSIDE,
        "dynamic_long_side": SORT_LSIDE,
    }
    for name, sort_algo in sort_algos.items():
        packer = newPacker(rotation=True, sort_algo=sort_algo)
        eff_w = width
        eff_h = height
        if eff_w <= 0 or eff_h <= 0:
            continue
        estimate = int((eff_w * eff_h) // (wprod * lprod)) + 5
        for i in range(estimate):
            packer.add_rect(wprod, lprod, i)
        packer.add_bin(eff_w, eff_h)
        packer.pack()
        positions = [(x, y, w, h) for (_, x, y, w, h, _) in packer.rect_list()]
        variants[name] = positions

    return variants
