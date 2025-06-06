import pytest
from packing_app.core import algorithms


def test_interlocked_shift_even(monkeypatch):
    """Even layers should be shifted when margin allows."""
    base_positions = [
        (100, 0, 100, 100),
        (200, 0, 100, 100),
    ]

    def fake_greedy(pallet_w, pallet_l, box_w, box_l):
        return len(base_positions), base_positions

    monkeypatch.setattr(algorithms, "pack_rectangles_mixed_greedy", fake_greedy)

    count, base_layers, interlocked_layers = algorithms.compute_interlocked_layout(
        500, 200, 100, 100, num_layers=2, shift_even=True
    )

    assert count == len(base_positions)
    assert base_layers == [base_positions, base_positions]
    shifted = [(x + 50, y, w, h) for x, y, w, h in base_positions]
    assert interlocked_layers == [base_positions, shifted]
