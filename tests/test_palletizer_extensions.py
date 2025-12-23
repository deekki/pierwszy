from palletizer_core.engine import PalletInputs, build_layouts
from palletizer_core.models import Carton, Pallet
from palletizer_core.selector import PatternSelector


def _inputs():
    return PalletInputs(
        pallet_w=1200,
        pallet_l=800,
        pallet_h=1500,
        box_w=200,
        box_l=150,
        box_h=100,
        thickness=0,
        spacing=5,
        slip_count=0,
        num_layers=1,
        max_stack=0,
        include_pallet_height=False,
    )


def test_extended_library_increases_results():
    inputs = _inputs()
    baseline = build_layouts(
        inputs,
        maximize_mixed=False,
        center_enabled=False,
        center_mode="Cała warstwa",
        shift_even=False,
        extended_library=False,
    )
    extended = build_layouts(
        inputs,
        maximize_mixed=False,
        center_enabled=False,
        center_mode="Cała warstwa",
        shift_even=False,
        extended_library=True,
    )

    assert len(extended.layouts) > len(baseline.layouts)


def test_dynamic_variants_add_keys():
    carton = Carton(width=200, length=150)
    pallet = Pallet(width=1200, length=800)
    selector = PatternSelector(carton, pallet)

    patterns = selector.generate_all(dynamic_variants=True)

    assert any(name.startswith("dynamic_") for name in patterns)


def test_sanity_filter_removes_single_carton_columns(monkeypatch):
    bad_layout = [
        (0.0, 0.0, 10.0, 10.0),
        (20.0, 0.0, 10.0, 10.0),
        (40.0, 0.0, 10.0, 10.0),
    ]
    good_layout = [
        (0.0, 0.0, 10.0, 10.0),
        (0.0, 10.0, 10.0, 10.0),
    ]

    def fake_generate_all(self, **kwargs):
        return {"bad_layout": bad_layout, "good_layout": good_layout}

    monkeypatch.setattr(PatternSelector, "generate_all", fake_generate_all)

    inputs = PalletInputs(
        pallet_w=100,
        pallet_l=100,
        pallet_h=1500,
        box_w=10,
        box_l=10,
        box_h=100,
        thickness=0,
        spacing=0,
        slip_count=0,
        num_layers=1,
        max_stack=0,
        include_pallet_height=False,
    )

    result = build_layouts(
        inputs,
        maximize_mixed=False,
        center_enabled=False,
        center_mode="Cała warstwa",
        shift_even=False,
        filter_sanity=True,
    )

    layout_names = {name for _, _, name in result.layouts}
    assert "Bad layout" not in layout_names
    assert "Good Layout" in layout_names
