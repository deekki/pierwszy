import types

from palletizer_core import Carton, Pallet
from packing_app.gui.tab_pallet import TabPallet, PalletInputs


class Dummy:
    group_cartons = TabPallet.group_cartons
    center_layout = TabPallet.center_layout
    _build_layouts = TabPallet._build_layouts
    _update_row_by_row_stats = TabPallet._update_row_by_row_stats

    def __init__(self):
        def var(val):
            return types.SimpleNamespace(get=lambda: val)

        class ReadVar:
            def __init__(self, value="0"):
                self.value = value

            def set(self, value):
                self.value = value

            def get(self):
                return self.value

        self.maximize_mixed = var(False)
        self.shift_even_var = var(False)
        self.center_var = var(False)
        self.center_mode_var = var("Cała warstwa")
        self.row_by_row_vertical_var = ReadVar()
        self.row_by_row_horizontal_var = ReadVar()


def test_row_by_row_selected_by_default():
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

    assert any(name == "Row by row" for _, __, name in result.layouts)
    assert result.best_layout_name == "Row by row"


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


def test_row_by_row_counts_reflect_orientation():
    dummy = Dummy()

    carton = Carton(250, 150, 0)
    pallet = Pallet(1000, 800, 0)
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
    row_entry = next(
        layout for layout in result.layouts if layout[2] == "Row by row"
    )

    count, coords, _ = row_entry
    assert count == len(coords)
    assert dummy.row_by_row_vertical_var.get() == "8"
    assert dummy.row_by_row_horizontal_var.get() == "12"

