import types
from packing_app.gui import tab_pallet
from packing_app.gui.tab_pallet import (
    TabPallet,
    PalletInputs,
    LayoutComputation,
)


class DummyVar:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def dummy_tab():
    d = types.SimpleNamespace()
    d.pallet_w_var = types.SimpleNamespace(get=lambda: '100', set=lambda v: None)
    d.pallet_l_var = types.SimpleNamespace(get=lambda: '120', set=lambda v: None)
    d.pallet_h_var = types.SimpleNamespace(get=lambda: '150', set=lambda v: None)
    d.box_w_var = types.SimpleNamespace(get=lambda: '10', set=lambda v: None)
    d.box_l_var = types.SimpleNamespace(get=lambda: '20', set=lambda v: None)
    d.box_h_var = types.SimpleNamespace(get=lambda: '30', set=lambda v: None)
    d.num_layers_var = types.SimpleNamespace(get=lambda: '1', set=lambda v: None)
    d.layers = [[(0,0,10,20)]]
    d.num_layers = 1
    d.layer_patterns = ['']
    d.transformations = ['Brak']
    d.draw_pallet = lambda: None
    d.update_summary = lambda: None
    return d


def test_gather_and_apply_roundtrip(monkeypatch):
    tab = dummy_tab()
    data = TabPallet.gather_pattern_data(tab, 'demo')
    assert data['name'] == 'demo'
    new = dummy_tab()
    TabPallet.apply_pattern_data(new, data)
    assert new.layers == tab.layers
    assert new.num_layers == 1


def make_raw_tab():
    tab = object.__new__(TabPallet)
    tab.center_var = DummyVar(False)
    tab.center_mode_var = DummyVar("Cała warstwa")
    tab.shift_even_var = DummyVar(False)
    tab.maximize_mixed = DummyVar(False)
    tab.row_by_row_vertical_var = DummyVar(0)
    tab.row_by_row_horizontal_var = DummyVar(0)
    tab._row_by_row_user_modified = False
    tab._updating_row_by_row = False
    tab.products_per_carton_var = DummyVar("1")
    tab._updating_products_per_carton = False
    tab._last_2d_products_per_carton = ""
    tab.pattern_scores = {}
    tab.best_layout_key = ""
    return tab


def test_read_inputs_adjusts_layers():
    tab = object.__new__(TabPallet)
    tab.pallet_w_var = DummyVar("1000")
    tab.pallet_l_var = DummyVar("1200")
    tab.pallet_h_var = DummyVar("150")
    tab.box_w_var = DummyVar("100")
    tab.box_l_var = DummyVar("120")
    tab.box_h_var = DummyVar("50")
    tab.cardboard_thickness_var = DummyVar("5")
    tab.spacing_var = DummyVar("0")
    tab.slip_count_var = DummyVar("2")
    tab.num_layers_var = DummyVar("1")
    tab.max_stack_var = DummyVar("1000")
    tab.include_pallet_height_var = DummyVar(False)

    inputs = TabPallet._read_inputs(tab)

    expected_layers = max(int((1000 - 0) // (50 + 10)), 0)
    assert inputs.num_layers == expected_layers
    assert tab.num_layers_var.get() == str(expected_layers)
    assert inputs.slip_count == 2


def test_validate_inputs_shows_warning(monkeypatch):
    tab = object.__new__(TabPallet)
    warnings = []
    monkeypatch.setattr(
        tab_pallet.messagebox, "showwarning", lambda *args, **kwargs: warnings.append(args)
    )
    inputs = PalletInputs(
        pallet_w=0,
        pallet_l=1,
        pallet_h=1,
        box_w=1,
        box_l=1,
        box_h=1,
        thickness=0,
        spacing=0,
        slip_count=1,
        num_layers=1,
        max_stack=0,
        include_pallet_height=False,
    )

    assert not TabPallet._validate_inputs(tab, inputs)
    assert warnings


def test_build_layouts_returns_best_pattern():
    tab = make_raw_tab()
    inputs = PalletInputs(
        pallet_w=1200,
        pallet_l=800,
        pallet_h=1500,
        box_w=200,
        box_l=150,
        box_h=100,
        thickness=0,
        spacing=0,
        slip_count=0,
        num_layers=1,
        max_stack=0,
        include_pallet_height=False,
    )

    result = TabPallet._build_layouts(tab, inputs)

    assert result.layouts
    assert result.best_layout_name in [layout[2] for layout in result.layouts]
    assert result.best_even
    assert result.best_odd


def test_finalize_results_updates_state():
    tab = make_raw_tab()
    calls = []

    def recorder(name):
        def _():
            calls.append(name)

        return _

    tab.update_transform_frame = recorder("transform")
    tab.update_layers = recorder("layers")
    tab.update_summary = recorder("summary")
    tab.sort_layers = recorder("sort")

    inputs = PalletInputs(
        pallet_w=100,
        pallet_l=100,
        pallet_h=100,
        box_w=10,
        box_l=10,
        box_h=10,
        thickness=0,
        spacing=0,
        slip_count=3,
        num_layers=2,
        max_stack=0,
        include_pallet_height=False,
    )
    result = LayoutComputation(
        layouts=[(1, [(0, 0, 10, 10)], "Demo")],
        layout_map={"Demo": 0},
        best_layout_name="Demo",
        best_even=[(0, 0, 10, 10)],
        best_odd=[(0, 0, 10, 10)],
    )

    TabPallet._finalize_results(tab, inputs, result)

    assert tab.layouts == result.layouts
    assert tab.best_layout_name == "Demo"
    assert tab.num_layers == 2
    assert tab.slip_count == 3
    assert set(calls) == {"transform", "layers", "summary", "sort"}
