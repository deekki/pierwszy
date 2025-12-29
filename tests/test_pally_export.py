import re

from palletizer_core.pally_export import (
    build_pally_json,
    iso_utc_now_ms,
    mirror_pattern,
)


def test_iso_format():
    value = iso_utc_now_ms()
    assert value.endswith("Z")
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", value)


def test_mirror():
    pattern = [{"x": 120.0, "y": 200.0, "r": [90], "g": [], "f": 1}]
    mirrored = mirror_pattern(pattern, pallet_w=800)
    assert mirrored[0]["x"] == 680.0
    assert mirrored[0]["y"] == 200.0
    assert mirrored[0]["r"] == [270]


def test_schema_keys_order():
    rects = [(0.0, 0.0, 100.0, 200.0)]
    data = build_pally_json(
        name="Test",
        pallet_w=800,
        pallet_l=1200,
        pallet_h=150,
        box_w=100,
        box_l=200,
        box_h=300,
        box_weight_g=500,
        layer_rects_list=[rects],
        slips_after=set(),
    )
    assert list(data.keys()) == [
        "name",
        "description",
        "dimensions",
        "productDimensions",
        "maxGrip",
        "maxGripAuto",
        "labelOrientation",
        "guiSettings",
        "dateModified",
        "layerTypes",
        "layers",
    ]


def test_separator_always_first():
    rects = [(0.0, 0.0, 100.0, 200.0)]
    data = build_pally_json(
        name="Test",
        pallet_w=800,
        pallet_l=1200,
        pallet_h=150,
        box_w=100,
        box_l=200,
        box_h=300,
        box_weight_g=500,
        layer_rects_list=[rects],
        slips_after=set(),
    )
    assert data["layerTypes"][0] == {
        "name": "Shim paper: Default",
        "class": "separator",
        "height": 1,
    }


def test_layers_slips():
    rects = [(0.0, 0.0, 100.0, 200.0)]
    data = build_pally_json(
        name="Test",
        pallet_w=800,
        pallet_l=1200,
        pallet_h=150,
        box_w=100,
        box_l=200,
        box_h=300,
        box_weight_g=500,
        layer_rects_list=[list(rects) for _ in range(6)],
        slips_after={4},
    )
    assert data["layers"][0] == "Shim paper: Default"
    assert data["layers"][5] == "Shim paper: Default"
    assert data["layers"].count("Shim paper: Default") == 2
