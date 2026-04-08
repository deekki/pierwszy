from packing_app.gui.empty_space_preview import (
    SHAPE_OBLONG,
    SHAPE_OVAL,
    SHAPE_ROUND,
    active_dimensions_for_shape,
)


def test_active_dimensions_for_round_shape():
    assert active_dimensions_for_shape(SHAPE_ROUND) == {"diameter"}


def test_active_dimensions_for_oval_shape():
    assert active_dimensions_for_shape(SHAPE_OVAL) == {"length", "width", "height"}


def test_active_dimensions_for_oblong_shape():
    assert active_dimensions_for_shape(SHAPE_OBLONG) == {"length", "diameter"}
