import types
from packing_app.gui.tab_pallet import TabPallet


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
