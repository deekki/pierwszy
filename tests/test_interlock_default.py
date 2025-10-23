import types

from palletizer_core import Carton, Pallet
from packing_app.gui.tab_pallet import TabPallet, PalletInputs


class Dummy:
    group_cartons = TabPallet.group_cartons
    center_layout = TabPallet.center_layout
    _build_layouts = TabPallet._build_layouts
    _manual_interlock_pattern = TabPallet._manual_interlock_pattern
    _parse_interlock_value = staticmethod(TabPallet._parse_interlock_value)
    _infer_interlock_orientation = staticmethod(
        TabPallet._infer_interlock_orientation
    )

    def __init__(self):
        def var(val):
            return types.SimpleNamespace(get=lambda: val)
        self.maximize_mixed = var(False)
        self.shift_even_var = var(False)
        self.center_var = var(False)
        self.center_mode_var = var("Cała warstwa")
        self.interlock_cols_var = var("0")
        self.interlock_rows_var = var("0")


def test_interlock_selected_by_default():
    dummy = Dummy()
    carton = Carton(200, 200, 0)
    pallet = Pallet(800, 600, 0)
    inputs = PalletInputs(
        pallet_w=pallet.width,
        pallet_l=pallet.length,
        pallet_h=pallet.height,
        box_w=carton.width,
        box_l=carton.length,
        box_h=carton.height,
        thickness=0,
        spacing=0,
        slip_count=0,
        num_layers=1,
        max_stack=0,
        include_pallet_height=False,
    )

    result = dummy._build_layouts(inputs)

    assert any(name == "Interlock" for _, __, name in result.layouts)
    assert result.best_layout_name == "Interlock"


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


def test_manual_interlock_respects_requested_grid():
    dummy = Dummy()
    dummy.interlock_cols_var = types.SimpleNamespace(get=lambda: "3")
    dummy.interlock_rows_var = types.SimpleNamespace(get=lambda: "2")

    carton = Carton(200, 200, 0)
    pallet = Pallet(800, 600, 0)
    inputs = PalletInputs(
        pallet_w=pallet.width,
        pallet_l=pallet.length,
        pallet_h=pallet.height,
        box_w=carton.width,
        box_l=carton.length,
        box_h=carton.height,
        thickness=0,
        spacing=0,
        slip_count=0,
        num_layers=1,
        max_stack=0,
        include_pallet_height=False,
    )

    result = dummy._build_layouts(inputs)
    interlock_entry = next(
        layout for layout in result.layouts if layout[2] == "Interlock"
    )

    count, coords, _ = interlock_entry
    assert count == 6
    widths = {round(w, 5) for _, _, w, _ in coords}
    heights = {round(h, 5) for _, _, _, h in coords}
    assert widths == {200}
    assert heights == {200}


def test_manual_interlock_falls_back_when_exceeding_space():
    dummy = Dummy()
    dummy.interlock_cols_var = types.SimpleNamespace(get=lambda: "10")
    dummy.interlock_rows_var = types.SimpleNamespace(get=lambda: "0")

    carton = Carton(200, 200, 0)
    pallet = Pallet(800, 600, 0)
    inputs = PalletInputs(
        pallet_w=pallet.width,
        pallet_l=pallet.length,
        pallet_h=pallet.height,
        box_w=carton.width,
        box_l=carton.length,
        box_h=carton.height,
        thickness=0,
        spacing=0,
        slip_count=0,
        num_layers=1,
        max_stack=0,
        include_pallet_height=False,
    )

    result = dummy._build_layouts(inputs)
    interlock_entry = next(
        layout for layout in result.layouts if layout[2] == "Interlock"
    )
    count, coords, _ = interlock_entry

    assert count == 12
    assert len(coords) == 12

