from __future__ import annotations

from collections.abc import Mapping

SHAPE_ROUND = "okrągły"
SHAPE_OVAL = "owalny"
SHAPE_OBLONG = "podłużny"


def active_dimensions_for_shape(shape: str) -> set[str]:
    if shape == SHAPE_ROUND:
        return {"diameter"}
    if shape == SHAPE_OVAL:
        return {"length", "width", "height"}
    return {"length", "diameter"}


def draw_pill_preview(
    canvas,
    *,
    shape: str,
    dimensions_mm: Mapping[str, float | None],
) -> None:
    """Rysuje uproszczony podgląd kapsułki na Canvasie Tk."""
    canvas.delete("pill_preview")
    canvas.update_idletasks()
    width = max(int(float(canvas.cget("width"))), 120)
    height = max(int(float(canvas.cget("height"))), 80)

    pad = 12
    cx = width / 2
    cy = height / 2
    max_w = width - 2 * pad
    max_h = height - 2 * pad

    if shape == SHAPE_ROUND:
        diameter_mm = _positive_or_none(dimensions_mm.get("diameter"))
        diameter_px = _scaled_size(diameter_mm, minimum=34, maximum=min(max_w, max_h), fallback=56)
        x0 = cx - diameter_px / 2
        y0 = cy - diameter_px / 2
        x1 = cx + diameter_px / 2
        y1 = cy + diameter_px / 2
        canvas.create_oval(
            x0, y0, x1, y1, fill="#f4b5b8", outline="#be6e75", width=2, tags="pill_preview"
        )
        canvas.create_oval(
            x0 + diameter_px * 0.2,
            y0 + diameter_px * 0.18,
            x0 + diameter_px * 0.55,
            y0 + diameter_px * 0.42,
            fill="#ffd9dd",
            outline="",
            tags="pill_preview",
        )
        return

    if shape == SHAPE_OVAL:
        length_mm = _positive_or_none(dimensions_mm.get("length"))
        width_mm = _positive_or_none(dimensions_mm.get("width"))
        height_mm = _positive_or_none(dimensions_mm.get("height"))

        length_px = _scaled_size(length_mm, minimum=64, maximum=max_w, fallback=88)
        width_px = _scaled_size(width_mm, minimum=32, maximum=max_h * 0.8, fallback=50)
        depth_ratio = _depth_ratio(height_mm, width_mm)

        x0 = cx - length_px / 2
        y0 = cy - width_px / 2
        x1 = cx + length_px / 2
        y1 = cy + width_px / 2
        canvas.create_oval(
            x0, y0, x1, y1, fill="#f2b0b3", outline="#bd6b73", width=2, tags="pill_preview"
        )
        gloss_h = max(width_px * 0.15, 6)
        canvas.create_oval(
            x0 + length_px * 0.18,
            y0 + width_px * (0.15 + 0.08 * depth_ratio),
            x0 + length_px * 0.7,
            y0 + width_px * (0.15 + 0.08 * depth_ratio) + gloss_h,
            fill="#ffdce0",
            outline="",
            tags="pill_preview",
        )
        return

    total_length_mm = _positive_or_none(dimensions_mm.get("length"))
    diameter_mm = _positive_or_none(dimensions_mm.get("diameter"))
    body_w = _scaled_size(diameter_mm, minimum=26, maximum=max_h * 0.75, fallback=36)
    total_length_px = _scaled_size(total_length_mm, minimum=70, maximum=max_w, fallback=96)
    total_length_px = max(total_length_px, body_w * 1.35)
    radius = body_w / 2

    x0 = cx - total_length_px / 2
    y0 = cy - body_w / 2
    x1 = cx + total_length_px / 2
    y1 = cy + body_w / 2

    canvas.create_rectangle(
        x0 + radius,
        y0,
        x1 - radius,
        y1,
        fill="#f1adb2",
        outline="#bb6872",
        width=2,
        tags="pill_preview",
    )
    canvas.create_oval(
        x0,
        y0,
        x0 + 2 * radius,
        y1,
        fill="#f1adb2",
        outline="#bb6872",
        width=2,
        tags="pill_preview",
    )
    canvas.create_oval(
        x1 - 2 * radius,
        y0,
        x1,
        y1,
        fill="#f1adb2",
        outline="#bb6872",
        width=2,
        tags="pill_preview",
    )
    canvas.create_oval(
        x0 + total_length_px * 0.22,
        y0 + body_w * 0.18,
        x0 + total_length_px * 0.56,
        y0 + body_w * 0.38,
        fill="#ffdadf",
        outline="",
        tags="pill_preview",
    )


def _scaled_size(value_mm: float | None, *, minimum: float, maximum: float, fallback: float) -> float:
    if value_mm is None:
        return min(maximum, fallback)
    clamped_mm = max(1.0, min(value_mm, 60.0))
    factor = clamped_mm / 60.0
    return minimum + (maximum - minimum) * factor


def _positive_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    return value if value > 0 else None


def _depth_ratio(height_mm: float | None, width_mm: float | None) -> float:
    if height_mm is None or width_mm is None or width_mm <= 0:
        return 0.5
    return max(0.2, min(height_mm / width_mm, 1.8))
