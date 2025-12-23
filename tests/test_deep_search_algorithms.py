from palletizer_core.algorithms import (
    generate_guillotine_layouts,
    generate_strip_layouts,
    pack_rectangles_2d,
)
from palletizer_core.engine import PalletInputs, build_layouts
from palletizer_core.signature import layout_signature


def _assert_layout_valid(layout, pallet_w, pallet_l):
    for x, y, w, length in layout:
        assert x >= -1e-6
        assert y >= -1e-6
        assert x + w <= pallet_w + 1e-6
        assert y + length <= pallet_l + 1e-6
    for i in range(len(layout)):
        ax, ay, aw, al = layout[i]
        for j in range(i + 1, len(layout)):
            bx, by, bw, bl = layout[j]
            overlap_x = ax < bx + bw - 1e-6 and bx < ax + aw - 1e-6
            overlap_y = ay < by + bl - 1e-6 and by < ay + al - 1e-6
            assert not (overlap_x and overlap_y)


def test_strip_dp_layouts_fit_and_deterministic():
    pallet_w, pallet_l = 120.0, 100.0
    box_w, box_l = 30.0, 20.0

    layouts_a = generate_strip_layouts(pallet_w, pallet_l, box_w, box_l, max_variants=10)
    layouts_b = generate_strip_layouts(pallet_w, pallet_l, box_w, box_l, max_variants=10)

    sig_a = [layout_signature(layout) for layout in layouts_a]
    sig_b = [layout_signature(layout) for layout in layouts_b]

    assert sig_a == sig_b
    for layout in layouts_a:
        _assert_layout_valid(layout, pallet_w, pallet_l)


def test_guillotine_layouts_fit_and_deterministic():
    pallet_w, pallet_l = 120.0, 100.0
    box_w, box_l = 30.0, 20.0

    layouts_a = generate_guillotine_layouts(pallet_w, pallet_l, box_w, box_l, max_variants=10)
    layouts_b = generate_guillotine_layouts(pallet_w, pallet_l, box_w, box_l, max_variants=10)

    sig_a = [layout_signature(layout) for layout in layouts_a]
    sig_b = [layout_signature(layout) for layout in layouts_b]

    assert sig_a == sig_b
    for layout in layouts_a:
        _assert_layout_valid(layout, pallet_w, pallet_l)


def test_strip_and_guillotine_counts_at_least_grid():
    pallet_w, pallet_l = 120.0, 100.0
    box_w, box_l = 30.0, 20.0

    grid_count, _ = pack_rectangles_2d(pallet_w, pallet_l, box_w, box_l)
    strip_best = max(
        (len(layout) for layout in generate_strip_layouts(pallet_w, pallet_l, box_w, box_l)),
        default=0,
    )
    guillotine_best = max(
        (len(layout) for layout in generate_guillotine_layouts(pallet_w, pallet_l, box_w, box_l)),
        default=0,
    )

    assert strip_best >= grid_count
    assert guillotine_best >= grid_count


def test_deep_search_build_layouts_deterministic():
    inputs = PalletInputs(
        pallet_w=1200,
        pallet_l=800,
        pallet_h=1500,
        box_w=200,
        box_l=150,
        box_h=100,
        thickness=0,
        spacing=5,
        slip_count=0,
        num_layers=1,
        max_stack=0,
        include_pallet_height=False,
    )
    result_a = build_layouts(
        inputs,
        maximize_mixed=False,
        center_enabled=False,
        center_mode="Cała warstwa",
        shift_even=False,
        deep_search=True,
        filter_sanity=True,
        result_limit=10,
    )
    result_b = build_layouts(
        inputs,
        maximize_mixed=False,
        center_enabled=False,
        center_mode="Cała warstwa",
        shift_even=False,
        deep_search=True,
        filter_sanity=True,
        result_limit=10,
    )

    sig_a = [layout_signature(layout) for _, layout, _ in result_a.layouts]
    sig_b = [layout_signature(layout) for _, layout, _ in result_b.layouts]

    assert result_a.best_layout_key == result_b.best_layout_key
    assert sig_a == sig_b
