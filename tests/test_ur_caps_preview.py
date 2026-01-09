import matplotlib.pyplot as plt

from packing_app.gui.tab_ur_caps import TabURCaps


def test_draw_layer_pattern_sequence_order(monkeypatch):
    tab = TabURCaps.__new__(TabURCaps)
    monkeypatch.setattr(tab, "_draw_approach_arrow", lambda *args, **kwargs: None)
    monkeypatch.setattr(tab, "_draw_empty_preview", lambda *args, **kwargs: None)

    payload = {
        "dimensions": {"width": 100.0, "length": 100.0},
        "productDimensions": {"width": 10.0, "length": 10.0},
    }
    pattern = [
        {"x": 10.0, "y": 10.0, "r": [0]},
        {"x": 20.0, "y": 10.0, "r": [0]},
        {"x": 30.0, "y": 10.0, "r": [0]},
    ]
    order = [2, 0, 1]

    fig, ax = plt.subplots()
    annotations: list[tuple[tuple[float, float], tuple[float, float]]] = []

    def capture_annotate(*args, **kwargs):
        annotations.append((kwargs["xytext"], kwargs["xy"]))

    monkeypatch.setattr(ax, "annotate", capture_annotate)

    tab._draw_layer_pattern(
        ax=ax,
        payload=payload,
        pattern=pattern,
        layer_idx=1,
        approach="normal",
        side="right",
        order=order,
    )

    assert annotations == [
        ((30.0, 10.0), (10.0, 10.0)),
        ((10.0, 10.0), (20.0, 10.0)),
    ]
