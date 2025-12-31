from palletizer_core.pattern_format import apply_pattern_data, gather_pattern_data


class DummyVar:
    def __init__(self, value=""):
        self.value = str(value)

    def get(self):
        return self.value

    def set(self, value):
        self.value = str(value)


class DummyTab:
    def __init__(self):
        self.pallet_w_var = DummyVar("1200")
        self.pallet_l_var = DummyVar("800")
        self.pallet_h_var = DummyVar("144")
        self.box_w_var = DummyVar("400")
        self.box_l_var = DummyVar("300")
        self.box_h_var = DummyVar("250")
        self.num_layers_var = DummyVar("2")
        self.layers = [
            [(0, 0, 10, 10)],
            [(5, 5, 10, 10)],
        ]
        self.carton_ids = []
        self.layer_patterns = []
        self.transformations = []
        self.undo_stack = []
        self.num_layers = len(self.layers)
        self.draw_calls = 0
        self.summary_calls = 0

    def draw_pallet(self, draw_idle: bool = False):
        self.draw_calls += 1

    def update_summary(self):
        self.summary_calls += 1

    def _set_layer_field(self, var, value):
        var.set(value)


def test_pattern_format_round_trip_applies_data():
    tab = DummyTab()
    data = gather_pattern_data(tab, name="demo")

    # Reset values to ensure apply_pattern_data overwrites them
    tab.pallet_w_var.set("0")
    tab.pallet_l_var.set("0")
    tab.pallet_h_var.set("0")
    tab.box_w_var.set("0")
    tab.box_l_var.set("0")
    tab.box_h_var.set("0")
    tab.layers = []
    tab.carton_ids = []
    tab.num_layers = 0
    tab.num_layers_var.set("0")

    apply_pattern_data(tab, data)

    assert float(tab.pallet_w_var.get()) == data["dimensions"]["width"]
    assert float(tab.pallet_l_var.get()) == data["dimensions"]["length"]
    assert float(tab.pallet_h_var.get()) == data["dimensions"]["height"]
    assert float(tab.box_w_var.get()) == data["productDimensions"]["width"]
    assert float(tab.box_l_var.get()) == data["productDimensions"]["length"]
    assert float(tab.box_h_var.get()) == data["productDimensions"]["height"]
    assert tab.layers == data["layers"]
    assert tab.num_layers == len(data["layers"])
    assert tab.draw_calls == 1
    assert tab.summary_calls == 1
