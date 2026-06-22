from palletizer_core import Carton, Pallet
from palletizer_core.engine import build_row_by_row_pattern, count_row_by_row_rows, normalize_row_by_row_counts


def _assert_inside(pattern, pallet):
    for x, y, w, h in pattern:
        assert x >= 0 and y >= 0
        assert x + w <= pallet.width
        assert y + h <= pallet.length


def test_manual_vertical_and_horizontal_lines_are_used():
    carton = Carton(200, 300, 100)
    pallet = Pallet(1000, 1200, 144)
    vertical, horizontal = normalize_row_by_row_counts(carton, pallet, 2, 2)
    pattern = build_row_by_row_pattern(carton, pallet, vertical, horizontal)
    assert count_row_by_row_rows(carton, pattern) == (2, 2)
    _assert_inside(pattern, pallet)


def test_manual_lines_are_clamped_to_fit_pallet():
    carton = Carton(400, 700, 100)
    pallet = Pallet(800, 1200, 144)
    vertical, horizontal = normalize_row_by_row_counts(carton, pallet, 9, 9)
    pattern = build_row_by_row_pattern(carton, pallet, vertical, horizontal)
    assert vertical * carton.length + horizontal * carton.width <= pallet.length
    assert count_row_by_row_rows(carton, pattern) == (vertical, horizontal)
    _assert_inside(pattern, pallet)
