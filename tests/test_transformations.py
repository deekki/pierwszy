from packing_app.gui.tab_pallet import TabPallet

def test_mirror_inverse():
    positions = [(10.0, 20.0, 30.0, 40.0)]
    pallet_w, pallet_l = 100.0, 80.0
    mirrored = TabPallet.apply_transformation(
        positions,
        "Odbicie wzdłuż dłuższego boku",
        pallet_w,
        pallet_l,
    )
    reverted = TabPallet.inverse_transformation(
        mirrored,
        "Odbicie wzdłuż dłuższego boku",
        pallet_w,
        pallet_l,
    )
    assert reverted == positions
