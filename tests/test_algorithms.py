import pytest

from packing_app.core.algorithms import maximize_mixed_layout


def test_maximize_mixed_layout_small_pallet_returns_empty():
    # carton dims larger than pallet dims so no orientation fits
    count, positions = maximize_mixed_layout(
        w_c=100, l_c=100, w_p=150, l_p=150, margin=0, initial_positions=[]
    )
    assert count == 0
    assert positions == []
