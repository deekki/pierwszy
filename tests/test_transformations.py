from palletizer_core.transformations import apply_transformation, inverse_transformation

def test_mirror_inverse():
    positions = [(10.0, 20.0, 30.0, 40.0)]
    pallet_w, pallet_l = 100.0, 80.0
    mirrored = apply_transformation(
        positions,
        "Odbicie wzdłuż dłuższego boku",
        pallet_w,
        pallet_l,
    )
    reverted = inverse_transformation(
        mirrored,
        "Odbicie wzdłuż dłuższego boku",
        pallet_w,
        pallet_l,
    )
    assert reverted == positions

def test_rotate180_inverse():
    positions = [(5.0, 5.0, 10.0, 20.0)]
    pallet_w, pallet_l = 40.0, 60.0
    rotated = apply_transformation(
        positions,
        "Obrót 180°",
        pallet_w,
        pallet_l,
    )
    reverted = inverse_transformation(
        rotated,
        "Obrót 180°",
        pallet_w,
        pallet_l,
    )
    assert reverted == positions
