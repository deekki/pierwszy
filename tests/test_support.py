from palletizer_core.support import (
    avg_support_fraction,
    min_support_fraction,
    support_fraction_per_box,
)


def test_support_full_coverage():
    layer_below = [(0.0, 0.0, 100.0, 100.0)]
    layer_above = [(0.0, 0.0, 100.0, 100.0)]
    support = support_fraction_per_box(layer_above, layer_below)
    assert support == [1.0]
    assert min_support_fraction(layer_above, layer_below) == 1.0
    assert avg_support_fraction(layer_above, layer_below) == 1.0


def test_support_half_coverage():
    layer_below = [(0.0, 0.0, 50.0, 100.0)]
    layer_above = [(0.0, 0.0, 100.0, 100.0)]
    support = support_fraction_per_box(layer_above, layer_below)
    assert support == [0.5]
    assert min_support_fraction(layer_above, layer_below) == 0.5
    assert avg_support_fraction(layer_above, layer_below) == 0.5


def test_support_no_coverage():
    layer_below = [(200.0, 0.0, 50.0, 100.0)]
    layer_above = [(0.0, 0.0, 100.0, 100.0)]
    support = support_fraction_per_box(layer_above, layer_below)
    assert support == [0.0]
    assert min_support_fraction(layer_above, layer_below) == 0.0
    assert avg_support_fraction(layer_above, layer_below) == 0.0
