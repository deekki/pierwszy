import types
import pytest

pytest.importorskip("tkinter")

from packing_app.gui.tab_pallet import TabPallet
from palletizer_core.stacking import compute_max_stack, compute_num_layers

class DummyPatch:
    def __init__(self, x=0, y=0):
        self._xy = (x, y)
    def get_xy(self):
        return self._xy
    def set_xy(self, xy):
        self._xy = xy

def var(val):
    ns = types.SimpleNamespace()
    ns.val = val
    ns.get = lambda: str(ns.val)
    ns.set = lambda v: setattr(ns, "val", v)
    return ns

def bvar(val):
    ns = types.SimpleNamespace()
    ns.val = val
    ns.get = lambda: ns.val
    ns.set = lambda v: setattr(ns, "val", v)
    return ns

def make_dummy():
    d = types.SimpleNamespace()
    d.pallet_w_var = var(100)
    d.pallet_l_var = var(100)
    d.cardboard_thickness_var = var(0)
    d.box_w_var = var(10)
    d.box_l_var = var(10)
    d.spacing_var = var(0)
    d.transformations = ["Brak", "Brak"]
    d.layer_patterns = ["A", "A"]
    d.layers = [[(0, 0, 10, 10)], [(0, 0, 10, 10)]]
    d.carton_ids = [[1], [1]]
    d.snap_position = lambda x, y, w, h, pw, pl, other: (x, y)
    d.inverse_transformation = lambda pos, trans, pw, pl: pos
    d.draw_pallet = lambda: None
    d.update_summary = lambda: None
    d.compute_pallet = lambda *a, **k: None
    d.odd_layout_var = var('A')
    d.even_layout_var = var('A')
    d.layers_linked = lambda: d.odd_layout_var.get() == d.even_layout_var.get()
    d.selected_indices = set()
    d.drag_info = None
    d.highlight_selection = lambda: None
    d.renumber_layer = lambda idx: d.carton_ids.__setitem__(idx, list(range(1, len(d.layers[idx]) + 1)))
    d.renumber_layers = lambda: [d.renumber_layer(i) for i in range(len(d.layers))]
    return d


def test_on_release_syncs_layers():
    dummy = make_dummy()
    dummy.drag_info = (0, 0, DummyPatch(5, 5))
    dummy.selected_indices = {(0, 0)}
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
    TabPallet.delete_selected_carton(dummy)
    assert len(dummy.layers[0]) == 1
    assert len(dummy.layers[1]) == 1

def test_renumber_after_insert_and_delete():
    dummy = make_dummy()
    TabPallet.insert_carton(dummy, 0, (5,5))
    assert dummy.carton_ids[0] == [1,2]
    dummy.selected_indices = {(0,0)}
    TabPallet.delete_selected_carton(dummy)
    assert dummy.carton_ids[0] == [1]

def test_no_cross_sync_when_patterns_differ():
    dummy = make_dummy()
    dummy.layer_patterns = ["A", "B"]
    dummy.drag_info = (0, 0, DummyPatch(2, 2))
    dummy.selected_indices = {(0, 0)}
    TabPallet.on_release(dummy, None)
    assert dummy.layers[0][0][:2] == (2, 2)
    assert dummy.layers[1][0][:2] == (0, 0)
    TabPallet.insert_carton(dummy, 0, (5, 5))
    assert len(dummy.layers[0]) == 2
    assert len(dummy.layers[1]) == 1
    dummy.selected_indices = {(0, 0)}
    TabPallet.delete_selected_carton(dummy)
    assert len(dummy.layers[0]) == 1
    assert len(dummy.layers[1]) == 1

def test_multi_rotate_delete():
    dummy = make_dummy()
    dummy.layers = [[(0, 0, 10, 20), (20, 0, 10, 20)], [(0, 0, 10, 20), (20, 0, 10, 20)]]
    dummy.carton_ids = [[1,2],[1,2]]
    dummy.selected_indices = {(0, 0), (0, 1)}
    TabPallet.rotate_selected_carton(dummy)
    for layer in dummy.layers:
        for x, y, w, h in layer:
            assert (w, h) == (20, 10)
    TabPallet.delete_selected_carton(dummy)
    assert dummy.layers[0] == [] and dummy.layers[1] == []

def test_distribution_commands():
    dummy = make_dummy()
    dummy.layers = [[(0,0,10,10),(40,0,10,10),(80,0,10,10)], [(0,0,10,10),(40,0,10,10),(80,0,10,10)]]
    dummy.carton_ids = [list(range(1,4)), list(range(1,4))]
    dummy.selected_indices = {(0,0),(0,1),(0,2)}
    TabPallet.distribute_selected_edges(dummy)
    xs = [pos[0] for pos in dummy.layers[0]]
    assert xs == pytest.approx([17.5,45.0,72.5])

    dummy = make_dummy()
    dummy.layers = [[(0,0,10,10),(10,0,10,10),(40,0,10,10),(80,0,10,10)], [(0,0,10,10),(10,0,10,10),(40,0,10,10),(80,0,10,10)]]
    dummy.carton_ids = [list(range(1,5)), list(range(1,5))]
    dummy.selected_indices = {(0,1),(0,2)}
    TabPallet.distribute_selected_between(dummy)
    xs = [dummy.layers[0][1][0], dummy.layers[0][2][0]]
    assert xs == pytest.approx([26.6666666667,53.3333333333])

def test_auto_distribution_respects_boundaries():
    dummy = make_dummy()
    dummy.layers = [[(0,0,60,10),(40,0,60,10)], [(0,0,60,10),(40,0,60,10)]]
    dummy.carton_ids = [[1,2],[1,2]]
    dummy.selected_indices = {(0,0),(0,1)}
    before = [pos[0] for pos in dummy.layers[0]]
    TabPallet.distribute_selected_edges(dummy)
    after = [pos[0] for pos in dummy.layers[0]]
    assert after == before  # not enough space to move

def test_adjust_spacing_clamps_to_zero():
    dummy = make_dummy()
    TabPallet.adjust_spacing(dummy, -5)
    assert dummy.spacing_var.get() == '0.0'

def test_multi_drag_moves_all_selected():
    dummy = make_dummy()
    dummy.layers = [[(0,0,10,10),(20,0,10,10)], [(0,0,10,10),(20,0,10,10)]]
    dummy.carton_ids = [[1,2],[1,2]]
    p1 = DummyPatch(5,5)
    p2 = DummyPatch(25,5)
    dummy.drag_info = [(0,0,p1,0,0),(0,1,p2,20,0)]
    dummy.selected_indices = {(0,0),(0,1)}
    TabPallet.on_release(dummy, None)
    assert dummy.layers[0][0][:2] == (5,5)
    assert dummy.layers[0][1][:2] == (25,5)
    assert dummy.layers[1][0][:2] == (5,5)
    assert dummy.layers[1][1][:2] == (25,5)

def test_sync_with_same_algo_different_transforms():
    dummy = make_dummy()
    dummy.transformations = ["Brak", "Odbicie wzdłuż dłuższego boku"]
    dummy.drag_info = (0, 0, DummyPatch(3, 3))
    dummy.selected_indices = {(0, 0)}
    TabPallet.on_release(dummy, None)
    assert dummy.layers[1][0][:2] == (3, 3)

def test_no_sync_when_algorithms_differ():
    dummy = make_dummy()
    dummy.transformations = ["Brak", "Odbicie wzdłuż dłuższego boku"]
    dummy.even_layout_var.set('B')
    dummy.drag_info = (0, 0, DummyPatch(4, 4))
    dummy.selected_indices = {(0, 0)}
    TabPallet.on_release(dummy, None)
    assert dummy.layers[1][0][:2] == (0, 0)


def test_height_limit_updates_layer_count():
    layers = compute_num_layers(
        max_stack=600,
        box_h=100,
        thickness=0,
        slip_count=0,
        include_pallet_height=True,
        pallet_h=144,
    )
    assert layers == 4


def test_layer_count_updates_height_limit():
    stack_height = compute_max_stack(
        num_layers=5,
        box_h=100,
        thickness=0,
        slip_count=0,
        include_pallet_height=True,
        pallet_h=144,
    )
    assert pytest.approx(stack_height) == 644


def test_sync_respects_pallet_toggle():
    layers = compute_num_layers(
        max_stack=500,
        box_h=100,
        thickness=0,
        slip_count=0,
        include_pallet_height=False,
        pallet_h=144,
    )
    assert layers == 5

    stack_height = compute_max_stack(
        num_layers=3,
        box_h=100,
        thickness=0,
        slip_count=0,
        include_pallet_height=False,
        pallet_h=144,
    )
    assert pytest.approx(stack_height) == 300
