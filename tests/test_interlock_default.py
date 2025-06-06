import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from palletizer_core import Carton, Pallet, PatternSelector
from packing_app.gui.tab_pallet import TabPallet


class Dummy:
    group_cartons = TabPallet.group_cartons
    center_layout = TabPallet.center_layout
    _get_default_layout = TabPallet._get_default_layout

    def __init__(self):
        def var(val):
            return types.SimpleNamespace(get=lambda: val)
        self.maximize_mixed = var(False)
        self.shift_even_var = var(False)
        self.center_var = var(False)
        self.center_mode_var = var("Cała warstwa")


def test_interlock_selected_by_default():
    dummy = Dummy()
    carton = Carton(200, 200, 0)
    pallet = Pallet(800, 600, 0)
    selector = PatternSelector(carton, pallet)

    patterns, name, _, _ = dummy._get_default_layout(
        selector, carton, pallet, pallet.width, pallet.length
    )

    assert "interlock" in patterns and patterns["interlock"], "interlock layout missing"
    assert name == "Interlock"

