import pytest

import palletizer_core.selector as selector
from palletizer_core import Carton, Pallet, PatternSelector, EvenOddSequencer


def _compute_best_layout(carton, pallet):
    """Replicate the core of TabPallet.compute_pallet."""
    selector = PatternSelector(carton, pallet)
    patterns = selector.generate_all()
    interlock_pattern = patterns.get("interlock")
    if interlock_pattern is None:
        best_name, best_pattern, _ = selector.best()
    else:
        best_name = "interlock"
        best_pattern = interlock_pattern
    seq = EvenOddSequencer(best_pattern, carton, pallet)
    even_base, odd_shifted = seq.best_shift()
    # shift_even_var defaults to True
    best_even = odd_shifted
    best_odd = even_base
    return best_name, best_even, best_odd


def test_compute_pallet_uses_interlock_and_offsets():
    carton = Carton(width=300, length=400)
    pallet = Pallet(width=1400, length=1100)

    best_name, even_layer, odd_layer = _compute_best_layout(carton, pallet)

    assert best_name == "interlock"

    # Even layer should be shifted by half the carton width
    expected_shift = carton.width / 2
    dx = even_layer[0][0] - odd_layer[0][0]
    dy = even_layer[0][1] - odd_layer[0][1]
    assert pytest.approx(dx) == expected_shift
    assert pytest.approx(dy) == 0


def test_even_odd_sequencer_shift():
    carton = Carton(width=300, length=400)
    pallet = Pallet(width=1400, length=1100)
    selector = PatternSelector(carton, pallet)
    pattern = selector.generate_all()["interlock"]

    seq = EvenOddSequencer(pattern, carton, pallet)
    even, odd = seq.best_shift()

    shifted = [(x + carton.width / 2, y, w, length) for x, y, w, length in even]
    assert odd == shifted


def test_stability_prefers_centered_layout():
    carton = Carton(width=50, length=50)
    pallet = Pallet(width=100, length=100)
    selector = PatternSelector(carton, pallet)

    centered = [(0, 0, 50, 50), (50, 50, 50, 50)]
    offcenter = [(0, 0, 50, 50), (0, 50, 50, 50)]

    c_score = selector.score(centered)
    o_score = selector.score(offcenter)

    assert c_score.stability > o_score.stability


def test_stability_penalizes_overhang():
    carton = Carton(width=50, length=50)
    pallet = Pallet(width=100, length=100)
    selector = PatternSelector(carton, pallet)

    inside = [(0, 0, 50, 50)]
    overhang = [(60, 0, 50, 50)]

    inside_score = selector.score(inside)
    over_score = selector.score(overhang)

    assert inside_score.stability > over_score.stability
    assert over_score.weakest_carton is not None
    assert over_score.weakest_support < inside_score.weakest_support


def test_generate_all_includes_rotated_column():
    carton = Carton(width=200, length=300)
    pallet = Pallet(width=1200, length=1000)
    selector = PatternSelector(carton, pallet)

    patterns = selector.generate_all()

    assert "column" in patterns
    assert "column_rotated" in patterns
    assert patterns["column"]
    assert patterns["column_rotated"]
    assert patterns["column"][0][2] == pytest.approx(carton.width)
    assert patterns["column_rotated"][0][2] == pytest.approx(carton.length)


def test_load_weights_without_yaml(tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text("layer_eff: 2.5\nstability: 3.5\n", encoding="utf-8")

    selector.load_weights.cache_clear()
    monkeypatch.setattr(selector, "yaml", None, raising=False)
    monkeypatch.setattr(selector.os.path, "join", lambda *args: str(settings_path))

    weights = selector.load_weights()

    assert weights["layer_eff"] == pytest.approx(2.5)
    assert weights["stability"] == pytest.approx(3.5)
    assert weights["cube_eff"] == pytest.approx(selector.DEFAULT_WEIGHTS["cube_eff"])

    selector.load_weights.cache_clear()
