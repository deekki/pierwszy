from packing_app.core.algorithms import (
    maximize_mixed_layout,
    pack_pinwheel,
    compute_interlocked_layout,
    pack_rectangles_mixed_max,
    pack_rectangles_dynamic,
)


def _overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)


def test_maximize_mixed_layout_small_pallet_returns_empty():
    # carton dims larger than pallet dims so no orientation fits
    count, positions = maximize_mixed_layout(
        w_c=100, l_c=100, w_p=150, l_p=150, margin=0, initial_positions=[]
    )
    assert count == 0
    assert positions == []


def test_pinwheel_layout_fits_and_no_collisions():
    pallet_w, pallet_l = 1000, 800
    box_w, box_l = 250, 150
    _, positions = pack_pinwheel(pallet_w, pallet_l, box_w, box_l)

    for x, y, w, length in positions:
        assert 0 <= x <= pallet_w - w
        assert 0 <= y <= pallet_l - length

    for i, pos in enumerate(positions):
        for other in positions[i + 1 :]:
            assert not _overlap(pos, other)


def test_pinwheel_fallback_for_small_area():
    pallet_w, pallet_l = 300, 200
    box_w, box_l = 180, 100
    _, positions = pack_pinwheel(pallet_w, pallet_l, box_w, box_l)

    for x, y, w, length in positions:
        assert 0 <= x <= pallet_w - w
        assert 0 <= y <= pallet_l - length

    for i, pos in enumerate(positions):
        for other in positions[i + 1 :]:
            assert not _overlap(pos, other)



def test_compute_interlocked_layout_returns_empty_for_small_pallet():
    count, base, interlocked = compute_interlocked_layout(
        pallet_w=100, pallet_l=100, box_w=150, box_l=150
    )

    assert count == 0
    assert base == [[] for _ in range(4)]
    assert interlocked == [[] for _ in range(4)]


def test_pack_rectangles_mixed_max_returns_empty_when_too_small():
    count, positions = pack_rectangles_mixed_max(
        width=40, height=40, wprod=60, lprod=40
    )
    assert count == 0
    assert positions == []


def test_pack_rectangles_mixed_max_grid_layout():
    pallet_w, pallet_l = 100, 100
    box_w, box_l = 50, 50
    count, positions = pack_rectangles_mixed_max(pallet_w, pallet_l, box_w, box_l)

    assert count == 4
    for x, y, w, h in positions:
        assert 0 <= x <= pallet_w - w
        assert 0 <= y <= pallet_l - h

    for i, pos in enumerate(positions):
        for other in positions[i + 1 :]:
            assert not _overlap(pos, other)


def test_pack_rectangles_mixed_max_mixed_orientations():
    pallet_w, pallet_l = 110, 100
    box_w, box_l = 60, 40
    count, positions = pack_rectangles_mixed_max(pallet_w, pallet_l, box_w, box_l)

    assert count == 3
    for x, y, w, h in positions:
        assert 0 <= x <= pallet_w - w
        assert 0 <= y <= pallet_l - h

    for i, pos in enumerate(positions):
        for other in positions[i + 1 :]:
            assert not _overlap(pos, other)


def test_pack_rectangles_dynamic_no_collisions():
    pallet_w, pallet_l = 1000, 800
    box_w, box_l = 250, 150
    count, positions = pack_rectangles_dynamic(pallet_w, pallet_l, box_w, box_l)
    assert count == len(positions)
    for x, y, w, h in positions:
        assert 0 <= x <= pallet_w - w
        assert 0 <= y <= pallet_l - h

    for i, pos in enumerate(positions):
        for other in positions[i + 1 :]:
            assert not _overlap(pos, other)
