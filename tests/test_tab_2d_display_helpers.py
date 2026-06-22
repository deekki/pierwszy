import types

from packing_app.gui.tab_2d import TabPacking2D


def test_display_grid_preserves_sparse_row_counts():
    dummy = types.SimpleNamespace()
    dummy._group_rows = TabPacking2D._group_rows.__get__(dummy)
    centers = [(5, 5), (15, 5), (5, 15)]

    new_centers, gap_x, gap_y, rows, cols = TabPacking2D._apply_display_grid(
        dummy, 30, 30, 5, centers, gap_x=2, gap_y=2
    )

    assert rows == 2
    assert cols == 2
    assert len(new_centers) == len(centers)
    assert gap_x == 2
    assert gap_y == 2


def test_centers_within_bounds_detects_manual_display_overflow():
    inside = [(5, 5), (15, 5)]
    outside = [(5, 5), (28, 5)]

    assert TabPacking2D._centers_within_bounds(None, 30, 30, 10, inside)
    assert not TabPacking2D._centers_within_bounds(None, 30, 30, 10, outside)
