from palletizer_core import Carton, Pallet
from palletizer_core.engine import PalletInputs, build_layouts, center_layout, group_cartons


def test_row_by_row_selected_by_default():
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

    result = build_layouts(
        inputs,
        maximize_mixed=False,
        center_enabled=False,
        center_mode="Cała warstwa",
        shift_even=False,
    )

    assert any(name == "Row by row" for _, __, name in result.layouts)
    assert result.best_layout_name == "Row by row"


def test_center_layout_keeps_groups_separate():
    # Two groups positioned at opposite sides of the pallet
    positions = [(0, 0, 50, 50), (150, 0, 50, 50)]
    pallet_w, pallet_l = 200, 100

    centered = center_layout(
        positions, pallet_w, pallet_l, True, "Poszczególne obszary"
    )
    groups_after = group_cartons(centered)

    # Groups should remain disjoint after centering
    assert len(groups_after) == 2


def test_row_by_row_counts_reflect_orientation():
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

    result = build_layouts(
        inputs,
        maximize_mixed=False,
        center_enabled=False,
        center_mode="Cała warstwa",
        shift_even=False,
    )
    row_entry = next(
        layout for layout in result.layouts if layout[2] == "Row by row"
    )

    count, coords, _ = row_entry
    assert count == len(coords)
    assert result.row_by_row_vertical == 2
    assert result.row_by_row_horizontal == 2
