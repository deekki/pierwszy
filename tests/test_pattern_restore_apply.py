from packing_app.gui.pallet_helpers import apply_pattern_selection_after_restore


class DummyTree:
    def __init__(self, selection):
        self._selection = selection

    def selection(self):
        return self._selection


class DummyTab:
    def __init__(self, selection):
        self._suspend_pattern_apply = True
        self.pattern_tree = DummyTree(selection)
        self.called = False

    def on_pattern_select(self):
        self.called = True


def test_apply_pattern_selection_after_restore_calls_when_selected():
    tab = DummyTab(("pattern_a",))
    applied = apply_pattern_selection_after_restore(tab, False, "pattern_a")
    assert applied is True
    assert tab._suspend_pattern_apply is False
    assert tab.called is True


def test_apply_pattern_selection_after_restore_skips_when_different():
    tab = DummyTab(("pattern_b",))
    applied = apply_pattern_selection_after_restore(tab, False, "pattern_a")
    assert applied is False
    assert tab._suspend_pattern_apply is False
    assert tab.called is False
