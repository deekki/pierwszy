import math
import random
import numpy as np

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



def compute_interlocked_layout(
    pallet_w, pallet_l, box_w, box_l, num_layers=4, shift_even=True
):
    """Return positions for standard and interlocked stacking.

    Parameters
    ----------
    pallet_w, pallet_l : float
        Dimensions of the pallet in mm.
    box_w, box_l : float
        Dimensions of the carton in mm.
    num_layers : int, optional
        Number of layers to generate. Default is 4.
    shift_even : bool, optional
        If ``True`` (default), even layers (2nd, 4th, ...) are shifted.
        If ``False``, odd layers are shifted instead.
    """
    count, base_positions = pack_rectangles_mixed_greedy(
        pallet_w, pallet_l, box_w, box_l
    )
    if not base_positions:
        empty_layers = [[] for _ in range(num_layers)]
        return 0, empty_layers, empty_layers

    base_layers = [list(base_positions) for _ in range(num_layers)]

    min_x = min(x for x, y, w, h in base_positions)
    max_x = max(x + w for x, y, w, h in base_positions)
    min_y = min(y for x, y, w, h in base_positions)
    max_y = max(y + h for x, y, w, h in base_positions)

    shift_x = 0.0
    shift_y = 0.0
    if min_x >= box_w / 2 and max_x + box_w / 2 <= pallet_w:
        shift_x = box_w / 2
    elif min_y >= box_l / 2 and max_y + box_l / 2 <= pallet_l:
        shift_y = box_l / 2

    interlocked_layers = []
    for layer_idx in range(num_layers):
        is_even = layer_idx % 2 == 1  # 1-based: even layer when index is odd
        should_shift = (shift_even and is_even) or (not shift_even and not is_even)
        if should_shift:
            shifted = [
                (x + shift_x, y + shift_y, w, h) for x, y, w, h in base_positions
            ]
            interlocked_layers.append(shifted)
        else:
            interlocked_layers.append(base_positions)

    return count, base_layers, interlocked_layers


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


def pack_rectangles_dynamic(width, height, wprod, lprod, margin=0):
    """Pack rectangles using a dynamic optimisation strategy.

    The routine relies on ``rectpack`` to explore many packing permutations with
    automatic rectangle rotation. The number of cartons is not predetermined;
    instead an upper bound is estimated from the available area and every box is
    submitted to the packer. The resulting list contains only the cartons that
    successfully fit inside the pallet area without overlapping.
    """

    try:
        from rectpack import newPacker
    except ImportError as exc:
        raise ImportError(
            "The 'rectpack' package is required for pack_rectangles_dynamic. "
            "Install it with 'pip install rectpack'."
        ) from exc

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
    """Pack rectangles using a dynamic maximisation approach.

    This is a convenience wrapper around :func:`maximize_mixed_layout` that
    starts with an empty layout and searches for the densest placement.  The
    algorithm explores both carton orientations recursively and keeps the best
    result found.  It resembles the strategies used by online palletisation
    tools such as Pally or OnPallet.
    """

    count, positions = maximize_mixed_layout(width, height, wprod, lprod, margin, [])
    return count, positions


def _build_cp_model(W_i, H_i, w_i, h_i, N):
    """Return (model, vars_) for the CP-SAT solver."""
    from ortools.sat.python import cp_model

    m = cp_model.CpModel()
    x = [m.NewIntVar(0, W_i, f"x{i}") for i in range(N)]
    y = [m.NewIntVar(0, H_i, f"y{i}") for i in range(N)]
    rot = [m.NewBoolVar(f"rot{i}") for i in range(N)]
    w_eff = [m.NewIntVar(min(w_i, h_i), max(w_i, h_i), f"w{i}") for i in range(N)]
    h_eff = [m.NewIntVar(min(w_i, h_i), max(w_i, h_i), f"h{i}") for i in range(N)]

    x_intv, y_intv = [], []
    for i in range(N):
        m.Add(w_eff[i] == rot[i] * h_i + (1 - rot[i]) * w_i)
        m.Add(h_eff[i] == rot[i] * w_i + (1 - rot[i]) * h_i)

        x_end = m.NewIntVar(0, W_i, f"x_end{i}")
        y_end = m.NewIntVar(0, H_i, f"y_end{i}")
        m.Add(x_end == x[i] + w_eff[i])
        m.Add(y_end == y[i] + h_eff[i])
        m.Add(x_end <= W_i)
        m.Add(y_end <= H_i)

        x_intv.append(m.NewIntervalVar(x[i], w_eff[i], x_end, f"x_int{i}"))
        y_intv.append(m.NewIntervalVar(y[i], h_eff[i], y_end, f"y_int{i}"))

    m.AddNoOverlap2D(x_intv, y_intv)
    return m, (x, y, w_eff, h_eff, rot)


def _solution_to_layout(sol, vars_, scale):
    x, y, w, h, _ = vars_
    return [
        (sol.Value(x[i]) / scale,
         sol.Value(y[i]) / scale,
         sol.Value(w[i]) / scale,
         sol.Value(h[i]) / scale)
        for i in range(len(x))
    ]


def enumerate_packings_wolny(
    width,
    height,
    wprod,
    lprod,
    *,
    want=15,
    time_first=20,
    time_each=20,
    seed=None,
):
    """Enumerate rectangle packings using a CP-SAT search (WOLNY)."""
    from ortools.sat.python import cp_model

    scale = 1000
    W_i, H_i = round(width * scale), round(height * scale)
    w_i, h_i = round(wprod * scale), round(lprod * scale)
    if seed is None:
        seed = random.randint(0, 1_000_000)
    if min(W_i, H_i, w_i, h_i) <= 0:
        return []

    area_big = W_i * H_i
    area_small = w_i * h_i
    N_target = area_big // area_small
    if N_target == 0:
        return []

    for N in range(N_target, 0, -1):
        model, vars_ = _build_cp_model(W_i, H_i, w_i, h_i, N)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_first
        if seed is not None:
            solver.parameters.random_seed = seed
        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            continue

        solutions = [_solution_to_layout(solver, vars_, scale)]

        def get_next():
            nonlocal solutions
            if len(solutions) >= want:
                return None

            solver2 = cp_model.CpSolver()
            solver2.parameters.max_time_in_seconds = time_each
            if seed is not None:
                solver2.parameters.random_seed = seed
            solver2.parameters.enumerate_all_solutions = True
            solver2.parameters.num_search_workers = 8

            class CB(cp_model.CpSolverSolutionCallback):
                def __init__(self):
                    super().__init__()
                    self.found = None

                def on_solution_callback(self):
                    rects = _solution_to_layout(self, vars_, scale)
                    if rects not in solutions:
                        self.found = rects
                        self.StopSearch()

            cb = CB()
            solver2.Solve(model, cb)
            if cb.found:
                solutions.append(cb.found)
                return cb.found
            return None

        return solutions, get_next
    return []


def pack_rectangles_wolny(width, height, wprod, lprod, *, time_limit=1.0):
    """Return first packing layout from :func:`enumerate_packings_wolny`."""
    result = enumerate_packings_wolny(
        width,
        height,
        wprod,
        lprod,
        want=1,
        time_first=time_limit,
        time_each=time_limit,
        seed=0,
    )
    if not result:
        return 0, []

    solutions, _ = result if isinstance(result, tuple) else (result, None)
    layout = solutions[0]
    return len(layout), [(x, y, w, h) for x, y, w, h in layout]

