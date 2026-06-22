from palletizer_core.metrics import compute_cube_efficiency


def test_cube_efficiency_uses_usable_height_without_carrier():
    eff = compute_cube_efficiency(
        cartons_per_layer=10, layers=4, box_w_ext=200, box_l_ext=300, box_h_ext=100,
        pallet_w=1000, pallet_l=1200, max_stack=1600, pallet_h=144, include_pallet_height=False,
    )
    assert eff == 40 * 200 * 300 * 100 / (1000 * 1200 * 1600)


def test_cube_efficiency_subtracts_carrier_height():
    eff = compute_cube_efficiency(
        cartons_per_layer=10, layers=4, box_w_ext=200, box_l_ext=300, box_h_ext=100,
        pallet_w=1000, pallet_l=1200, max_stack=1600, pallet_h=144, include_pallet_height=True,
    )
    assert eff == 40 * 200 * 300 * 100 / (1000 * 1200 * (1600 - 144))


def test_cube_efficiency_falls_back_to_layer_height_and_guards_zero():
    assert compute_cube_efficiency(cartons_per_layer=1, layers=1, box_w_ext=1, box_l_ext=1, box_h_ext=1, pallet_w=0, pallet_l=1) == 0
    assert compute_cube_efficiency(cartons_per_layer=2, layers=3, box_w_ext=100, box_l_ext=100, box_h_ext=100, pallet_w=1000, pallet_l=1000) == 0.02
