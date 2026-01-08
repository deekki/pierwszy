import re
from dataclasses import replace

from palletizer_core.pally_export import (
    PallyExportConfig,
    build_pally_json,
    iso_utc_now_ms,
    mirror_pattern,
    rects_to_pally_pattern,
)
from palletizer_core.signature import layout_signature


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


def test_mirror_handles_270_rotation():
    pattern = [{"x": 100.0, "y": 150.0, "r": [270], "g": [], "f": 1}]
    mirrored = mirror_pattern(pattern, pallet_w=800)
    assert mirrored[0]["x"] == 700.0
    assert mirrored[0]["r"] == [90]


def test_schema_keys_order():
    rects = [(0.0, 0.0, 100.0, 200.0)]
    data = build_pally_json(
        config=PallyExportConfig(
            name="Test",
            pallet_w=800,
            pallet_l=1200,
            pallet_h=150,
            box_w=100,
            box_l=200,
            box_h=300,
            box_weight_g=500,
            overhang_ends=0,
            overhang_sides=0,
        ),
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
        config=PallyExportConfig(
            name="Test",
            pallet_w=800,
            pallet_l=1200,
            pallet_h=150,
            box_w=100,
            box_l=200,
            box_h=300,
            box_weight_g=500,
            overhang_ends=0,
            overhang_sides=0,
        ),
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
        config=PallyExportConfig(
            name="Test",
            pallet_w=800,
            pallet_l=1200,
            pallet_h=150,
            box_w=100,
            box_l=200,
            box_h=300,
            box_weight_g=500,
            overhang_ends=0,
            overhang_sides=0,
        ),
        layer_rects_list=[list(rects) for _ in range(6)],
        slips_after={4},
    )
    assert data["layers"][0] == "Shim paper: Default"
    assert data["layers"][5] == "Shim paper: Default"
    assert data["layers"].count("Shim paper: Default") == 2


def test_base_slip_can_be_disabled():
    rects = [(0.0, 0.0, 100.0, 200.0)]
    data = build_pally_json(
        config=PallyExportConfig(
            name="Test",
            pallet_w=800,
            pallet_l=1200,
            pallet_h=150,
            box_w=100,
            box_l=200,
            box_h=300,
            box_weight_g=500,
            overhang_ends=0,
            overhang_sides=0,
        ),
        layer_rects_list=[rects],
        slips_after=set(),
        include_base_slip=False,
    )
    assert data["layers"][0].startswith("Layer type: ")
    assert "Shim paper: Default" not in data["layers"]


def test_swap_axes_and_mapping():
    rects = [(0.0, 0.0, 300.0, 200.0)]
    data = build_pally_json(
        config=PallyExportConfig(
            name="Test",
            pallet_w=1200,
            pallet_l=800,
            pallet_h=150,
            box_w=300,
            box_l=200,
            box_h=300,
            box_weight_g=500,
            overhang_ends=0,
            overhang_sides=0,
            swap_axes_for_pally=True,
        ),
        layer_rects_list=[rects],
        slips_after=set(),
    )
    assert data["dimensions"]["width"] == 800
    assert data["dimensions"]["length"] == 1200
    pattern = data["layerTypes"][1]["pattern"][0]
    assert pattern["x"] == 100.0
    assert pattern["y"] == 150.0
    assert data["productDimensions"]["width"] == 200
    assert data["productDimensions"]["length"] == 300


def test_quantization_rounds_to_step():
    rects = [(10.0, 20.0, 123.064, 200.064)]
    data = build_pally_json(
        config=PallyExportConfig(
            name="Test",
            pallet_w=800,
            pallet_l=1200,
            pallet_h=150,
            box_w=123.0,
            box_l=200.0,
            box_h=300,
            box_weight_g=500,
            overhang_ends=0,
            overhang_sides=0,
            quant_step_mm=0.5,
        ),
        layer_rects_list=[rects],
        slips_after=set(),
    )
    pattern = data["layerTypes"][1]["pattern"][0]
    assert pattern["x"] == 71.5
    assert pattern["y"] == 120.0


def test_quantization_prevents_noise():
    rects = [(10.0, 20.0, 200.0, 300.0)]
    data = build_pally_json(
        config=PallyExportConfig(
            name="Test",
            pallet_w=800,
            pallet_l=1200,
            pallet_h=150,
            box_w=200,
            box_l=300,
            box_h=300,
            box_weight_g=500,
            overhang_ends=0,
            overhang_sides=0,
            quant_step_mm=0.5,
        ),
        layer_rects_list=[rects],
        slips_after=set(),
    )
    pattern = data["layerTypes"][1]["pattern"][0]
    assert pattern["x"] == 110.0
    assert pattern["y"] == 170.0


def test_rotation_selection_with_label_orientation():
    rects = [
        (50.0, 50.0, 100.0, 200.0),
        (50.0, 900.0, 100.0, 200.0),
        (50.0, 50.0, 200.0, 100.0),
        (600.0, 50.0, 200.0, 100.0),
    ]
    pattern, _ = rects_to_pally_pattern(
        rects=rects,
        carton_w=100.0,
        carton_l=200.0,
        pallet_w=800.0,
        pallet_l=1200.0,
        quant_step_mm=1.0,
        label_orientation=180,
        placement_sequence="default",
    )

    rotations = {(item["x"], item["y"]): item["r"][0] for item in pattern}
    assert rotations[(100.0, 150.0)] == 180
    assert rotations[(100.0, 1000.0)] == 0
    assert rotations[(150.0, 100.0)] == 90
    assert rotations[(700.0, 100.0)] == 270


def test_layer_types_are_reused_for_repeating_patterns():
    rects_a = [(0.0, 0.0, 100.0, 200.0)]
    rects_b = [(0.0, 0.0, 200.0, 100.0)]
    payload = build_pally_json(
        config=PallyExportConfig(
            name="Test",
            pallet_w=800,
            pallet_l=1200,
            pallet_h=150,
            box_w=100,
            box_l=200,
            box_h=300,
            box_weight_g=500,
            overhang_ends=0,
            overhang_sides=0,
        ),
        layer_rects_list=[rects_a, rects_b, rects_a, rects_b, rects_a],
        slips_after=set(),
    )

    assert len(payload["layerTypes"]) == 3
    used_layers = set(payload["layers"])
    assert "Layer type: 3" not in used_layers
    assert "Layer type: 4" not in used_layers


def test_dedupe_tolerant_signature():
    base_layer = [(0.0, 0.0, 100.0, 200.0)]
    noisy_layer = [(0.0001, 0.0, 100.0002, 199.9999)]
    data = build_pally_json(
        config=PallyExportConfig(
            name="Test",
            pallet_w=800,
            pallet_l=1200,
            pallet_h=150,
            box_w=100,
            box_l=200,
            box_h=300,
            box_weight_g=500,
            overhang_ends=0,
            overhang_sides=0,
            signature_eps_mm=0.5,
        ),
        layer_rects_list=[base_layer, noisy_layer],
        slips_after=set(),
    )
    layer_types = [lt for lt in data["layerTypes"] if lt.get("class") == "layer"]
    assert len(layer_types) == 1


def test_large_value_quantization_to_half_mm():
    rects = [(0.0, 0.0, 400.0, 1676.128)]
    data = build_pally_json(
        config=PallyExportConfig(
            name="Test",
            pallet_w=1000,
            pallet_l=1200,
            pallet_h=100,
            box_w=400,
            box_l=1676.0,
            box_h=300,
            box_weight_g=500,
            overhang_ends=0,
            overhang_sides=0,
            quant_step_mm=0.5,
        ),
        layer_rects_list=[rects],
        slips_after=set(),
    )
    item = data["layerTypes"][1]["pattern"][0]
    assert item["y"] == 838.0


def test_label_orientation_flips_towards_back_edge():
    rects = [(300.0, 950.0, 100.0, 200.0)]
    data = build_pally_json(
        config=PallyExportConfig(
            name="Test",
            pallet_w=800,
            pallet_l=1200,
            pallet_h=150,
            box_w=100,
            box_l=200,
            box_h=300,
            box_weight_g=500,
            overhang_ends=0,
            overhang_sides=0,
            label_orientation=0,
        ),
        layer_rects_list=[rects],
        slips_after=set(),
    )
    pattern = data["layerTypes"][1]["pattern"][0]
    assert pattern["r"] == [180]


def test_pattern_sorted_deterministically():
    rects = [(200.0, 300.0, 100.0, 200.0), (0.0, 0.0, 100.0, 200.0)]
    data = build_pally_json(
        config=PallyExportConfig(
            name="Test",
            pallet_w=800,
            pallet_l=1200,
            pallet_h=150,
            box_w=100,
            box_l=200,
            box_h=300,
            box_weight_g=500,
            overhang_ends=0,
            overhang_sides=0,
        ),
        layer_rects_list=[rects],
        slips_after=set(),
    )
    pattern = data["layerTypes"][1]["pattern"]
    coords = [(item["x"], item["y"]) for item in pattern]
    assert coords == [(50.0, 100.0), (250.0, 400.0)]


def test_pattern_sequence_columns():
    rects = [(200.0, 0.0, 100.0, 200.0), (0.0, 300.0, 100.0, 200.0)]
    data = build_pally_json(
        config=PallyExportConfig(
            name="Test",
            pallet_w=800,
            pallet_l=1200,
            pallet_h=150,
            box_w=100,
            box_l=200,
            box_h=300,
            box_weight_g=500,
            overhang_ends=0,
            overhang_sides=0,
            placement_sequence="columns",
        ),
        layer_rects_list=[rects],
        slips_after=set(),
    )
    coords = [(item["x"], item["y"]) for item in data["layerTypes"][1]["pattern"]]
    assert coords == [(50.0, 400.0), (250.0, 100.0)]


def test_pattern_sequence_snake_rows():
    rects = [
        (0.0, 0.0, 100.0, 100.0),
        (200.0, 0.0, 100.0, 100.0),
        (0.0, 200.0, 100.0, 100.0),
        (200.0, 200.0, 100.0, 100.0),
    ]
    data = build_pally_json(
        config=PallyExportConfig(
            name="Test",
            pallet_w=400,
            pallet_l=400,
            pallet_h=150,
            box_w=100,
            box_l=100,
            box_h=300,
            box_weight_g=500,
            overhang_ends=0,
            overhang_sides=0,
            placement_sequence="snake",
        ),
        layer_rects_list=[rects],
        slips_after=set(),
    )
    coords = [(item["x"], item["y"]) for item in data["layerTypes"][1]["pattern"]]
    assert coords == [(50.0, 50.0), (250.0, 50.0), (250.0, 250.0), (50.0, 250.0)]


def test_pattern_sequence_center_priority():
    rects = [
        (0.0, 0.0, 100.0, 100.0),
        (300.0, 0.0, 100.0, 100.0),
        (150.0, 100.0, 100.0, 100.0),
    ]
    data = build_pally_json(
        config=PallyExportConfig(
            name="Test",
            pallet_w=400,
            pallet_l=400,
            pallet_h=150,
            box_w=100,
            box_l=100,
            box_h=300,
            box_weight_g=500,
            overhang_ends=0,
            overhang_sides=0,
            placement_sequence="center",
        ),
        layer_rects_list=[rects],
        slips_after=set(),
    )
    coords = [(item["x"], item["y"]) for item in data["layerTypes"][1]["pattern"]]
    assert coords[0] == (200.0, 150.0)


def test_alt_pattern_uses_configured_mode():
    rects = [(0.0, 0.0, 100.0, 200.0)]
    data = build_pally_json(
        config=PallyExportConfig(
            name="Test",
            pallet_w=800,
            pallet_l=1200,
            pallet_h=150,
            box_w=100,
            box_l=200,
            box_h=300,
            box_weight_g=500,
            overhang_ends=0,
            overhang_sides=0,
            alt_layout="altPattern",
            approach="normal",
            alt_approach="inverse",
        ),
        layer_rects_list=[rects],
        slips_after=set(),
    )
    layer = next(lt for lt in data["layerTypes"] if lt.get("class") == "layer")
    assert layer["altPattern"] == list(reversed(layer["pattern"]))
    assert layer["approach"] == "normal"
    assert layer["altApproach"] == "inverse"


def test_manual_permutation_applies_to_pattern():
    rects = [
        (0.0, 0.0, 100.0, 200.0),
        (150.0, 0.0, 100.0, 200.0),
        (0.0, 250.0, 100.0, 200.0),
    ]
    config = PallyExportConfig(
        name="Test",
        pallet_w=800,
        pallet_l=1200,
        pallet_h=150,
        box_w=100,
        box_l=200,
        box_h=300,
        box_weight_g=500,
        overhang_ends=0,
        overhang_sides=0,
    )
    _, signature_rects = rects_to_pally_pattern(
        rects,
        carton_w=config.box_w,
        carton_l=config.box_l,
        pallet_w=config.pallet_w,
        pallet_l=config.pallet_l,
        quant_step_mm=config.quant_step_mm,
        label_orientation=config.label_orientation,
        placement_sequence=config.placement_sequence,
    )
    signature = str(layout_signature(signature_rects, eps=config.signature_eps_mm))

    manual_order = [2, 0, 1]
    data_auto = build_pally_json(
        config=config,
        layer_rects_list=[rects],
        slips_after=set(),
    )
    data_manual = build_pally_json(
        config=config,
        layer_rects_list=[rects],
        slips_after=set(),
        manual_orders_by_signature={signature: manual_order},
    )

    expected = [data_auto["layerTypes"][1]["pattern"][idx] for idx in manual_order]
    assert data_manual["layerTypes"][1]["pattern"] == expected


def test_manual_permutation_applies_to_alt_pattern():
    rects = [(0.0, 0.0, 100.0, 200.0), (200.0, 0.0, 100.0, 200.0)]
    config = PallyExportConfig(
        name="Test",
        pallet_w=800,
        pallet_l=1200,
        pallet_h=150,
        box_w=100,
        box_l=200,
        box_h=300,
        box_weight_g=500,
        overhang_ends=0,
        overhang_sides=0,
        alt_layout="altPattern",
    )
    _, signature_rects = rects_to_pally_pattern(
        rects,
        carton_w=config.box_w,
        carton_l=config.box_l,
        pallet_w=config.pallet_w,
        pallet_l=config.pallet_l,
        quant_step_mm=config.quant_step_mm,
        label_orientation=config.label_orientation,
        placement_sequence=config.placement_sequence,
    )
    signature = str(layout_signature(signature_rects, eps=config.signature_eps_mm))

    manual_order = [1, 0]
    data_auto = build_pally_json(
        config=config,
        layer_rects_list=[rects],
        slips_after=set(),
    )
    data_manual = build_pally_json(
        config=config,
        layer_rects_list=[rects],
        slips_after=set(),
        manual_orders_by_signature={signature: manual_order},
    )

    expected_pattern = [data_auto["layerTypes"][1]["pattern"][idx] for idx in manual_order]
    expected_alt_pattern = [
        data_auto["layerTypes"][1]["altPattern"][idx] for idx in manual_order
    ]
    layer = next(lt for lt in data_manual["layerTypes"] if lt.get("class") == "layer")
    assert layer["pattern"] == expected_pattern
    assert layer["altPattern"] == expected_alt_pattern


def test_manual_permutation_can_differ_for_alt_pattern():
    rects = [
        (0.0, 0.0, 100.0, 200.0),
        (200.0, 0.0, 100.0, 200.0),
        (400.0, 0.0, 100.0, 200.0),
    ]
    config = PallyExportConfig(
        name="Test",
        pallet_w=800,
        pallet_l=1200,
        pallet_h=150,
        box_w=100,
        box_l=200,
        box_h=300,
        box_weight_g=500,
        overhang_ends=0,
        overhang_sides=0,
        alt_layout="altPattern",
    )
    _, signature_rects = rects_to_pally_pattern(
        rects,
        carton_w=config.box_w,
        carton_l=config.box_l,
        pallet_w=config.pallet_w,
        pallet_l=config.pallet_l,
        quant_step_mm=config.quant_step_mm,
        label_orientation=config.label_orientation,
        placement_sequence=config.placement_sequence,
    )
    signature = str(layout_signature(signature_rects, eps=config.signature_eps_mm))

    manual_order_right = [2, 0, 1]
    manual_order_left = [1, 2, 0]
    data_auto = build_pally_json(
        config=config,
        layer_rects_list=[rects],
        slips_after=set(),
    )
    data_manual = build_pally_json(
        config=config,
        layer_rects_list=[rects],
        slips_after=set(),
        manual_orders_by_signature_right={signature: manual_order_right},
        manual_orders_by_signature_left={signature: manual_order_left},
    )

    expected_pattern = [data_auto["layerTypes"][1]["pattern"][idx] for idx in manual_order_right]
    expected_alt_pattern = [
        data_auto["layerTypes"][1]["altPattern"][idx] for idx in manual_order_left
    ]
    layer = next(lt for lt in data_manual["layerTypes"] if lt.get("class") == "layer")
    assert layer["pattern"] == expected_pattern
    assert layer["altPattern"] == expected_alt_pattern


def test_inverse_approach_does_not_reorder_pattern_without_manual_order():
    rects = [
        (0.0, 0.0, 100.0, 200.0),
        (150.0, 0.0, 100.0, 200.0),
        (0.0, 250.0, 100.0, 200.0),
    ]
    config_normal = PallyExportConfig(
        name="Test",
        pallet_w=800,
        pallet_l=1200,
        pallet_h=150,
        box_w=100,
        box_l=200,
        box_h=300,
        box_weight_g=500,
        overhang_ends=0,
        overhang_sides=0,
        approach="normal",
        alt_approach="normal",
    )
    config_inverse = PallyExportConfig(
        name="Test",
        pallet_w=800,
        pallet_l=1200,
        pallet_h=150,
        box_w=100,
        box_l=200,
        box_h=300,
        box_weight_g=500,
        overhang_ends=0,
        overhang_sides=0,
        approach="inverse",
        alt_approach="inverse",
    )

    normal = build_pally_json(config=config_normal, layer_rects_list=[rects], slips_after=set())
    inverse = build_pally_json(config=config_inverse, layer_rects_list=[rects], slips_after=set())

    normal_layer = next(lt for lt in normal["layerTypes"] if lt.get("class") == "layer")
    inverse_layer = next(lt for lt in inverse["layerTypes"] if lt.get("class") == "layer")

    assert inverse_layer["pattern"] == normal_layer["pattern"]
    assert inverse_layer["approach"] == "inverse"


def test_manual_order_has_priority_over_inverse_approach():
    rects = [
        (0.0, 0.0, 100.0, 200.0),
        (150.0, 0.0, 100.0, 200.0),
        (0.0, 250.0, 100.0, 200.0),
    ]
    base_config = PallyExportConfig(
        name="Test",
        pallet_w=800,
        pallet_l=1200,
        pallet_h=150,
        box_w=100,
        box_l=200,
        box_h=300,
        box_weight_g=500,
        overhang_ends=0,
        overhang_sides=0,
    )
    _, signature_rects = rects_to_pally_pattern(
        rects,
        carton_w=base_config.box_w,
        carton_l=base_config.box_l,
        pallet_w=base_config.pallet_w,
        pallet_l=base_config.pallet_l,
        quant_step_mm=base_config.quant_step_mm,
        label_orientation=base_config.label_orientation,
        placement_sequence=base_config.placement_sequence,
    )
    signature = str(layout_signature(signature_rects, eps=base_config.signature_eps_mm))

    manual_order = [2, 0, 1]
    normal = build_pally_json(
        config=replace(base_config, approach="normal", alt_approach="normal"),
        layer_rects_list=[rects],
        slips_after=set(),
    )
    manual_override = build_pally_json(
        config=replace(base_config, approach="inverse", alt_approach="inverse"),
        layer_rects_list=[rects],
        slips_after=set(),
        manual_orders_by_signature_right={signature: manual_order},
        manual_orders_by_signature_left={signature: manual_order},
    )

    expected_pattern = [
        next(lt for lt in normal["layerTypes"] if lt.get("class") == "layer")["pattern"][idx]
        for idx in manual_order
    ]
    manual_layer = next(lt for lt in manual_override["layerTypes"] if lt.get("class") == "layer")
    result_pattern = manual_layer["pattern"]

    assert result_pattern == expected_pattern
    assert manual_layer["approach"] == "inverse"
