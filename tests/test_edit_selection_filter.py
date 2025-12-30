from packing_app.gui.pallet_helpers import filter_selection_for_layer


def test_filter_selection_for_layer_keeps_active_only():
    selected = {(0, 1), (1, 2), (0, 3)}
    assert filter_selection_for_layer(selected, 0) == {(0, 1), (0, 3)}
    assert filter_selection_for_layer(selected, 1) == {(1, 2)}
