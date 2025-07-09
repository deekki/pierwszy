"""Rectangle packing utilities for pallet layers.

Implements several heuristics to place as many identical boxes as
possible on a single pallet layer.  The algorithms explored are:
- Bottom-Left-Fill
- Skyline (level height)
- MaxRects (Best Area Fit and Best Short Side Fit)
- Guillotine split (shorter axis first)

Every algorithm runs with rectangles in three sort orders and the
result with the highest box count (and highest fill ratio as a tie
breaker) is returned.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Callable

import matplotlib.pyplot as plt


@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int

    def as_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}


def _overlap(a: Rect, b: Rect) -> bool:
    return not (
        a.x + a.w <= b.x or b.x + b.w <= a.x or a.y + a.h <= b.y or b.y + b.h <= a.y
    )


def _inside(rect: Rect, W: int, H: int) -> bool:
    return rect.x >= 0 and rect.y >= 0 and rect.x + rect.w <= W and rect.y + rect.h <= H


# ---------------------------------------------------------------------------
# Packing algorithms
# ---------------------------------------------------------------------------

def bottom_left_fill(W: int, H: int, bw: int, bh: int) -> List[Rect]:
    oriented = [(bw, bh)] if bw == bh else [(bw, bh), (bh, bw)]
    placed: List[Rect] = []
    points = [(0, 0)]
    while points:
        points.sort(key=lambda p: (p[1], p[0]))
        px, py = points.pop(0)
        found = False
        for w, h in oriented:
            rect = Rect(px, py, w, h)
            if not _inside(rect, W, H):
                continue
            if all(not _overlap(rect, r) for r in placed):
                placed.append(rect)
                if (px + w, py) not in points:
                    points.append((px + w, py))
                if (px, py + h) not in points:
                    points.append((px, py + h))
                points = [
                    p
                    for p in points
                    if p[0] < W and p[1] < H and all(not (p[0] >= r.x and p[0] < r.x + r.w and p[1] >= r.y and p[1] < r.y + r.h) for r in placed)
                ]
                found = True
                break
        if not found:
            continue
    return placed


def skyline_level(W: int, H: int, bw: int, bh: int) -> List[Rect]:
    oriented = [(bw, bh)] if bw == bh else [(bw, bh), (bh, bw)]
    heights = [0] * W
    placed: List[Rect] = []
    while True:
        best = None
        best_y = None
        best_x = None
        best_dim = None
        for w, h in oriented:
            if w > W or h > H:
                continue
            for x in range(0, W - w + 1):
                y = max(heights[x : x + w])
                if y + h > H:
                    continue
                if best_y is None or y < best_y or (y == best_y and x < best_x):
                    best_y = y
                    best_x = x
                    best_dim = (w, h)
                    best = Rect(x, y, w, h)
        if best is None:
            break
        w, h = best_dim
        placed.append(best)
        for i in range(best_x, best_x + w):
            heights[i] = best_y + h
    return placed


def _split_free(fr: Rect, w: int, h: int) -> List[Rect]:
    res = []
    if fr.w - w > 0:
        res.append(Rect(fr.x + w, fr.y, fr.w - w, h))
    if fr.h - h > 0:
        res.append(Rect(fr.x, fr.y + h, fr.w, fr.h - h))
    if fr.w - w > 0 and fr.h - h > 0:
        res.append(Rect(fr.x + w, fr.y + h, fr.w - w, fr.h - h))
    return [r for r in res if r.w > 0 and r.h > 0]


def _prune(free: List[Rect]) -> List[Rect]:
    pruned = []
    for r in free:
        if not any(
            r != o
            and r.x >= o.x
            and r.y >= o.y
            and r.x + r.w <= o.x + o.w
            and r.y + r.h <= o.y + o.h
            for o in free
        ):
            pruned.append(r)
    return pruned


def maxrects(W: int, H: int, bw: int, bh: int, score: Callable[[Rect, int, int], int]) -> List[Rect]:
    oriented = [(bw, bh)] if bw == bh else [(bw, bh), (bh, bw)]
    free = [Rect(0, 0, W, H)]
    placed: List[Rect] = []
    while True:
        best = None
        best_score = None
        best_rect = None
        for fr in free:
            for w, h in oriented:
                if w <= fr.w and h <= fr.h:
                    s = score(fr, w, h)
                    if best_score is None or s < best_score:
                        best_score = s
                        best = (w, h)
                        best_rect = fr
        if best_rect is None:
            break
        w, h = best
        placed.append(Rect(best_rect.x, best_rect.y, w, h))
        free.remove(best_rect)
        free.extend(_split_free(best_rect, w, h))
        free = _prune(free)
    return placed


def score_area(fr: Rect, w: int, h: int) -> int:
    return fr.w * fr.h - w * h


def score_short_side(fr: Rect, w: int, h: int) -> int:
    return min(fr.w - w, fr.h - h)


def guillotine(W: int, H: int, bw: int, bh: int) -> List[Rect]:
    oriented = [(bw, bh)] if bw == bh else [(bw, bh), (bh, bw)]
    free = [Rect(0, 0, W, H)]
    placed: List[Rect] = []
    while True:
        target = None
        orient = None
        for fr in free:
            for w, h in oriented:
                if w <= fr.w and h <= fr.h:
                    target = fr
                    orient = (w, h)
                    break
            if target:
                break
        if target is None:
            break
        w, h = orient
        placed.append(Rect(target.x, target.y, w, h))
        free.remove(target)
        right = Rect(target.x + w, target.y, target.w - w, h)
        top = Rect(target.x, target.y + h, target.w, target.h - h)
        if target.w - w <= target.h - h:
            if right.w > 0 and right.h > 0:
                free.append(right)
            if top.w > 0 and top.h > 0:
                free.append(top)
        else:
            if top.w > 0 and top.h > 0:
                free.append(top)
            if right.w > 0 and right.h > 0:
                free.append(right)
        if target.w - w > 0 and target.h - h > 0:
            free.append(Rect(target.x + w, target.y + h, target.w - w, target.h - h))
    return placed


# ---------------------------------------------------------------------------
# Local compaction and helpers
# ---------------------------------------------------------------------------

def _overlap_x(a: Rect, b: Rect) -> bool:
    return not (a.x + a.w <= b.x or b.x + b.w <= a.x)


def _overlap_y(a: Rect, b: Rect) -> bool:
    return not (a.y + a.h <= b.y or b.y + b.h <= a.y)


def greedy_compact(rects: List[Rect], W: int, H: int) -> None:
    changed = True
    while changed:
        changed = False
        for r in rects:
            min_y = 0
            for o in rects:
                if o is r:
                    continue
                if _overlap_x(r, o):
                    min_y = max(min_y, o.y + o.h)
            if min_y < r.y:
                r.y = min_y
                changed = True
            min_x = 0
            for o in rects:
                if o is r:
                    continue
                if _overlap_y(r, o):
                    min_x = max(min_x, o.x + o.w)
            if min_x < r.x:
                r.x = min_x
                changed = True


def validate(layout: List[dict], W: int, H: int, bw: int, bh: int) -> bool:
    rects = [Rect(r["x"], r["y"], r["w"], r["h"]) for r in layout]
    for r in rects:
        if not _inside(r, W, H):
            return False
        if (r.w, r.h) not in {(bw, bh), (bh, bw)}:
            return False
    for i, a in enumerate(rects):
        for b in rects[i + 1 :]:
            if _overlap(a, b):
                return False
    return True


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def pack_layer(pal_w: int, pal_h: int, box_w: int, box_h: int, visualise: bool = False) -> List[dict]:
    """Return best packing layout for a single pallet layer."""

    algos: List[Callable[[int, int, int, int], List[Rect]]] = [
        bottom_left_fill,
        skyline_level,
        lambda W, H, bw, bh: maxrects(W, H, bw, bh, score_area),
        lambda W, H, bw, bh: maxrects(W, H, bw, bh, score_short_side),
        guillotine,
    ]

    best_layout: List[Rect] = []
    best_count = 0
    best_ratio = 0.0

    for algo in algos:
        layout = algo(pal_w, pal_h, box_w, box_h)
        greedy_compact(layout, pal_w, pal_h)
        count = len(layout)
        ratio = sum(r.w * r.h for r in layout) / (pal_w * pal_h)
        if count > best_count or (count == best_count and ratio > best_ratio):
            best_layout = layout
            best_count = count
            best_ratio = ratio

    result = [r.as_dict() for r in best_layout]

    if visualise:
        _visualise(result, pal_w, pal_h)

    return result


def _visualise(layout: List[dict], W: int, H: int) -> None:
    fig, ax = plt.subplots()
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.set_facecolor("#d9d9d9")
    border = plt.Rectangle((0, 0), W, H, fill=False, edgecolor="black", linewidth=2)
    ax.add_patch(border)
    for r in layout:
        rect = plt.Rectangle((r["x"], r["y"]), r["w"], r["h"], facecolor="#008bd1", alpha=0.9, edgecolor="black")
        ax.add_patch(rect)
    plt.show()


if __name__ == "__main__":
    layout = pack_layer(1200, 800, 300, 200, visualise=True)
    print("Rectangles placed:", len(layout))
    print(
        "Fill ratio:",
        sum(r["w"] * r["h"] for r in layout) / (1200 * 800),
    )
