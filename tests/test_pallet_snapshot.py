from palletizer_core.engine import PalletInputs

from packing_app.core.pallet_snapshot import PalletSnapshot


def test_pallet_snapshot_records_transformed_layers():
    inputs = PalletInputs(
        pallet_w=1200,
        pallet_l=800,
        pallet_h=1500,
        box_w=200,
        box_l=150,
        box_h=100,
        thickness=2,
        spacing=5,
        slip_count=1,
        num_layers=2,
        max_stack=0,
        include_pallet_height=False,
    )

    layers = [
        [(0, 0, 200, 150)],
        [(0, 0, 200, 150)],
    ]
    transformations = ["Brak", "Obrót 180°"]

    snapshot = PalletSnapshot.from_layers(
        inputs=inputs,
        layers=layers,
        transformations=transformations,
        slips_after={1},
    )

    assert snapshot.pallet_w == 1200
    assert snapshot.box_w == 200
    assert snapshot.slip_count == 1
    assert snapshot.layers[0] == layers[0]
    assert snapshot.transformations == transformations
    assert snapshot.layer_rects_list[0][0] == (0, 0, 200, 150)
    assert snapshot.layer_rects_list[1][0] == (1000, 650, 200, 150)
    assert snapshot.slips_after == {1}
    assert snapshot.num_layers == 2

