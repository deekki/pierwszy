import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from palletizer_core.models import Carton, Pallet
from palletizer_core.sequencer import EvenOddSequencer


def test_shift_uses_available_clearance():
    pattern = [(0, 0, 100, 100)]
    seq = EvenOddSequencer(pattern, Carton(100, 100), Pallet(210, 210))
    even, odd = seq.best_shift()
    assert odd[0] == (50.0, 50.0, 100, 100)


def test_shift_prefers_largest_offset_direction():
    pattern = [(20, 0, 100, 100)]
    seq = EvenOddSequencer(pattern, Carton(100, 100), Pallet(160, 100))
    even, odd = seq.best_shift()
    assert odd[0][0] == pytest.approx(60.0)


def test_no_clearance_results_in_no_shift():
    pattern = [(0, 0, 100, 100)]
    seq = EvenOddSequencer(pattern, Carton(100, 100), Pallet(100, 100))
    even, odd = seq.best_shift()
    assert odd == even
