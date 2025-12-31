from copy import deepcopy

from packing_app.gui.layer_propagation import propagate_carton_delta


def test_propagate_carton_delta_updates_matching_layers():
    layers = [
        [(0.0, 0.0, 1.0, 1.0), (2.0, 0.0, 1.0, 1.0)],
        [(5.0, 5.0, 1.0, 1.0)],
        [(0.0, 0.0, 1.0, 1.0), (2.0, 0.0, 1.0, 1.0)],
        [(5.0, 5.0, 1.0, 1.0)],
        [(0.0, 0.0, 1.0, 1.0), (2.0, 0.0, 1.0, 1.0)],
    ]
    layer_patterns = ["odd", "even", "odd", "even", "odd"]

    moved_layers = deepcopy(layers)
    delta = (0.5, -0.25)
    source_idx = (0, 1)

    x, y, w, h = moved_layers[source_idx[0]][source_idx[1]]
    moved_layers[source_idx[0]][source_idx[1]] = (x + delta[0], y + delta[1], w, h)

    updated = propagate_carton_delta(
        moved_layers,
        layer_patterns,
        source_idx[0],
        source_idx[1],
        delta,
        reference_box=layers[source_idx[0]][source_idx[1]],
    )

    assert {(2, 1), (4, 1)}.issubset(set(updated))
    assert moved_layers[2][1][:2] == (layers[2][1][0] + delta[0], layers[2][1][1] + delta[1])
    assert moved_layers[4][1][:2] == (layers[4][1][0] + delta[0], layers[4][1][1] + delta[1])
    assert moved_layers[1][0] == layers[1][0]
    assert moved_layers[3][0] == layers[3][0]
