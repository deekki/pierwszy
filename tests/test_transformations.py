import types
from packing_app.gui.tab_pallet import TabPallet

def test_rotation_inverse():
    dummy = types.SimpleNamespace()
    positions = [(10.0, 20.0, 30.0, 40.0)]
    pallet_w, pallet_l = 100.0, 80.0
    rotated = TabPallet.apply_transformation(
        dummy, positions, "Rotacja 90°", pallet_w, pallet_l, 30.0, 40.0
    )
    reverted = TabPallet.inverse_transformation(
        dummy, rotated, "Rotacja 90°", pallet_w, pallet_l, 30.0, 40.0
    )
    assert reverted == positions
