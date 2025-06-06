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


def test_center_layout_keeps_groups_separate():
    dummy = Dummy()
    # Enable centering and use the per-area mode
    dummy.center_var = types.SimpleNamespace(get=lambda: True)
    dummy.center_mode_var = types.SimpleNamespace(get=lambda: "Poszczególne obszary")

    # Two groups positioned at opposite sides of the pallet
    positions = [(0, 0, 50, 50), (150, 0, 50, 50)]
    pallet_w, pallet_l = 200, 100

    centered = dummy.center_layout(positions, pallet_w, pallet_l)
    groups_after = dummy.group_cartons(centered)

    # Groups should remain disjoint after centering
    assert len(groups_after) == 2

