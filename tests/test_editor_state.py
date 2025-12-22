from packing_app.gui.editor_state import EditorState


def test_lpm_click_selects_single():
    state = EditorState(selected=set())
    result = state.on_press(hit_index=2, button=1, ctrl=False, shift=False, x=0, y=0)

    assert state.selected == {2}
    assert result["selection_changed"] is True


def test_lpm_drag_keeps_selection_after_release():
    state = EditorState(selected={1, 2})
    state.on_press(hit_index=1, button=1, ctrl=False, shift=False, x=0, y=0)
    state.on_motion(x=10, y=0)
    state.on_release(button=1, x=10, y=0)

    assert state.selected == {1, 2}


def test_ppm_on_selected_does_not_change_selection():
    state = EditorState(selected={1, 2})
    result = state.on_press(hit_index=1, button=3, ctrl=False, shift=False, x=0, y=0)

    assert state.selected == {1, 2}
    assert result["selection_changed"] is False


def test_ppm_on_non_selected_with_group_does_not_override():
    state = EditorState(selected={1, 2})
    result = state.on_press(hit_index=3, button=3, ctrl=False, shift=False, x=0, y=0)

    assert state.selected == {1, 2}
    assert result["selection_changed"] is False


def test_ctrl_lpm_toggles_selection():
    state = EditorState(selected={1})
    state.on_press(hit_index=2, button=1, ctrl=True, shift=False, x=0, y=0)

    assert state.selected == {1, 2}
