import sys

from palletizer_core import pattern_io


def test_save_and_load_pattern(tmp_path, monkeypatch):
    monkeypatch.setenv("PALLETIZER_PATTERN_DIR", str(tmp_path))
    data = {
        "name": "demo",
        "dimensions": {"width": 100, "length": 120, "height": 150},
        "productDimensions": {"width": 10, "length": 20, "height": 30},
        "layers": [[[0, 0, 10, 20]]],
    }
    pattern_io.save_pattern("demo", data)
    assert pattern_io.list_pattern_files() == ["demo"]
    loaded = pattern_io.load_pattern("demo")
    assert loaded == data


def test_default_pattern_dir_uses_cwd(tmp_path, monkeypatch):
    monkeypatch.delenv("PALLETIZER_PATTERN_DIR", raising=False)
    monkeypatch.setattr(sys, "argv", ["not_a_real_file"])
    monkeypatch.chdir(tmp_path)
    data = {
        "name": "demo",
        "dimensions": {"width": 100, "length": 120, "height": 150},
        "productDimensions": {"width": 10, "length": 20, "height": 30},
        "layers": [[[0, 0, 10, 20]]],
    }

    pattern_dir = pattern_io.ensure_pattern_dir()
    assert pattern_dir == str(tmp_path / "data" / "pallet_patterns")

    pattern_io.save_pattern("demo", data)
    loaded = pattern_io.load_pattern("demo")
    assert loaded == data
