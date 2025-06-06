from packing_app.core import algorithms


def test_dense_not_worse_than_greedy():
    """pack_rectangles_mixed_max should place at least as many boxes as greedy."""
    cases = [
        (3, 2, 2, 1),
        (4, 4, 3, 2),
        (5, 3, 2, 2),
    ]
    for W, H, w, l in cases:
        g_count, _ = algorithms.pack_rectangles_mixed_greedy(W, H, w, l)
        m_count, _ = algorithms.pack_rectangles_mixed_max(W, H, w, l)
        assert m_count >= g_count
