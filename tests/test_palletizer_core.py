import pytest

from palletizer_core import Carton, Pallet, PatternSelector, EvenOddSequencer


def _compute_best_layout(carton, pallet):
    """Replicate the core of TabPallet.compute_pallet."""
    selector = PatternSelector(carton, pallet)
    patterns = selector.generate_all()
    interlock_pattern = patterns.get("interlock")
    if interlock_pattern is None:
        best_name, best_pattern, _ = selector.best()
    else:
        best_name = "interlock"
        best_pattern = interlock_pattern
    seq = EvenOddSequencer(best_pattern, carton, pallet)
    even_base, odd_shifted = seq.best_shift()
    # shift_even_var defaults to True
    best_even = odd_shifted
    best_odd = even_base
    return best_name, best_even, best_odd


def test_compute_pallet_uses_interlock_and_offsets():
    carton = Carton(width=300, length=400)
    pallet = Pallet(width=1400, length=1100)

    best_name, even_layer, odd_layer = _compute_best_layout(carton, pallet)

    assert best_name == "interlock"

    # Even layer should be shifted by half the carton width
    expected_shift = carton.width / 2
    dx = even_layer[0][0] - odd_layer[0][0]
    dy = even_layer[0][1] - odd_layer[0][1]
    assert pytest.approx(dx) == expected_shift
    assert pytest.approx(dy) == 0


def test_even_odd_sequencer_shift():
    carton = Carton(width=300, length=400)
    pallet = Pallet(width=1400, length=1100)
    selector = PatternSelector(carton, pallet)
    pattern = selector.generate_all()["interlock"]

    seq = EvenOddSequencer(pattern, carton, pallet)
    even, odd = seq.best_shift()

    shifted = [(x + carton.width / 2, y, w, l) for x, y, w, l in even]
    assert odd == shifted
