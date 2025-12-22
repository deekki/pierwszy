import pytest

from palletizer_core.units import parse_float


def test_parse_float_accepts_comma():
    assert parse_float("12,5") == 12.5


def test_parse_float_strips_whitespace():
    assert parse_float("  10.0 ") == 10.0


def test_parse_float_rejects_empty():
    with pytest.raises(ValueError):
        parse_float("")
