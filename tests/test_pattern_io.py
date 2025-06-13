import packing_app.core.pattern_io as pattern_io


def test_save_and_load_pattern(tmp_path, monkeypatch):
    monkeypatch.setattr(pattern_io, "PATTERN_DIR", tmp_path)
    data = {
        "name": "demo",
        "dimensions": {"width": 100, "length": 120, "height": 150},
        "productDimensions": {"width": 10, "length": 20, "height": 30},
        "layers": [[[0, 0, 10, 20]]],
    }
    pattern_io.save_pattern("demo", data)
    assert pattern_io.list_patterns() == ["demo"]
    loaded = pattern_io.load_pattern("demo")
    assert loaded == data
