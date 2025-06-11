from packing_app.core.algorithms import (
    maximize_mixed_layout,
    pack_pinwheel,
    compute_interlocked_layout,
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
