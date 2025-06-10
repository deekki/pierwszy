import types
import pytest
from packing_app.gui.tab_pallet import TabPallet

class DummyPatch:
    def __init__(self, x=0, y=0):
        self._xy = (x, y)
    def get_xy(self):
        return self._xy
    def set_xy(self, xy):
        self._xy = xy

def var(val):
    return types.SimpleNamespace(get=lambda: str(val))

def make_dummy():
    d = types.SimpleNamespace()
    d.pallet_w_var = var(100)
    d.pallet_l_var = var(100)
    d.cardboard_thickness_var = var(0)
    d.box_w_var = var(10)
    d.box_l_var = var(10)
    d.transformations = ["Brak", "Brak"]
    d.layers = [[(0, 0, 10, 10)], [(0, 0, 10, 10)]]
    d.snap_position = lambda x, y, w, h, pw, pl, other: (x, y)
    d.inverse_transformation = lambda pos, trans, pw, pl, bw, bl: pos
    d.draw_pallet = lambda: None
    d.update_summary = lambda: None
    d.selected_indices = set()
    d.drag_target = None
    return d

def test_on_release_syncs_layers():
    dummy = make_dummy()
    dummy.drag_target = (0, 0, DummyPatch(5, 5))
    TabPallet.on_release(dummy, None)
    assert dummy.layers[0][0][:2] == (5, 5)
    assert dummy.layers[1][0][:2] == (5, 5)

def test_insert_and_delete_sync():
    dummy = make_dummy()
    TabPallet.insert_carton(dummy, 0, (10, 10))
    assert len(dummy.layers[0]) == 2
    assert len(dummy.layers[1]) == 2
    assert dummy.layers[0][-1][:2] == (10, 10)
    assert dummy.layers[1][-1][:2] == (10, 10)
    dummy.selected_indices = {(0, 0)}
    TabPallet.delete_selected_cartons(dummy)
    assert len(dummy.layers[0]) == 1
    assert len(dummy.layers[1]) == 1

def test_rotate_and_distribute():
    dummy = make_dummy()
    dummy.layers = [[(0, 0, 10, 20), (20, 0, 10, 20)], [(0, 0, 10, 20), (20, 0, 10, 20)]]
    dummy.selected_indices = {(0, 0), (0, 1)}
    TabPallet.rotate_selected_cartons(dummy)
    assert dummy.layers[0][0][2:] == (20, 10)
    assert dummy.layers[0][1][2:] == (20, 10)

    TabPallet.distribute_selected_edge(dummy)
    gap = (100 - 40) / 3
    assert dummy.layers[0][0][0] == pytest.approx(gap)
    assert dummy.layers[0][1][0] == pytest.approx(gap * 2 + 20)

    # distribute between
    dummy.layers[0] = [(0, 0, 10, 10), (15, 0, 10, 10), (40, 0, 10, 10)]
    dummy.layers[1] = list(dummy.layers[0])
    dummy.selected_indices = {(0, 1)}
    TabPallet.distribute_selected_between(dummy)
    assert dummy.layers[0][1][0] == pytest.approx(20)
