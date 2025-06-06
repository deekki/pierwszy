from palletizer_core.sequencer import EvenOddSequencer
from palletizer_core.models import Carton, Pallet


def test_best_shift_mirrors_to_fit():
    pallet = Pallet(400, 300)
    carton = Carton(100, 80)
    pattern = [(-30, -40, 100, 80)]
    seq = EvenOddSequencer(pattern, carton, pallet)
    even, odd = seq.best_shift()

    assert even == pattern
    assert all(
        0 <= x <= pallet.width - w and 0 <= y <= pallet.length - l
        for x, y, w, l in odd
    )
    assert odd[0][0] == pattern[0][0] + carton.width / 2
    assert odd[0][1] == pattern[0][1] + carton.length / 2
