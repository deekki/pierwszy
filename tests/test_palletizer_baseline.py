from palletizer_core.engine import PalletInputs, build_layouts


def test_build_layouts_baseline_matches_previous_results():
    inputs = PalletInputs(
        pallet_w=1200,
        pallet_l=800,
        pallet_h=1500,
        box_w=200,
        box_l=150,
        box_h=100,
        thickness=0,
        spacing=5,
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

    assert result.best_layout_name == "Mixed"
    assert len(result.layouts) == 6

    inputs_alt = PalletInputs(
        pallet_w=1200,
        pallet_l=800,
        pallet_h=1500,
        box_w=300,
        box_l=200,
        box_h=100,
        thickness=0,
        spacing=5,
        slip_count=0,
        num_layers=1,
        max_stack=0,
        include_pallet_height=False,
    )
    result_alt = build_layouts(
        inputs_alt,
        maximize_mixed=False,
        center_enabled=False,
        center_mode="Cała warstwa",
        shift_even=False,
    )

    assert result_alt.best_layout_name == "Dynamic"
    assert len(result_alt.layouts) == 6
