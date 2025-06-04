import sys
import types
import math

# Provide a minimal numpy stub if numpy is not installed
if 'numpy' not in sys.modules:
    numpy_stub = types.ModuleType('numpy')
    random_stub = types.ModuleType('random')
    import random as py_random
    random_stub.uniform = py_random.uniform
    numpy_stub.random = random_stub
    sys.modules['numpy'] = numpy_stub

from packing_app.core.algorithms import pack_rectangles_2d, pack_hex_top_down


def test_pack_rectangles_basic():
    count, positions = pack_rectangles_2d(10, 5, 3, 2)
    expected_positions = [
        (0, 0, 3, 2), (0, 2, 3, 2),
        (3, 0, 3, 2), (3, 2, 3, 2),
        (6, 0, 3, 2), (6, 2, 3, 2),
    ]
    assert count == 6
    assert positions == expected_positions


def test_pack_rectangles_with_margin():
    count, positions = pack_rectangles_2d(6, 4, 3, 2, margin=2)
    assert count == 1
    assert positions == [(0, 0, 3, 2)]


def test_pack_rectangles_insufficient():
    assert pack_rectangles_2d(4, 3, 5, 2) == (0, [])


def test_pack_hex_top_down_small():
    centers = pack_hex_top_down(4, 4, 2)
    expected = [
        (1.0, 1.0),
        (3.0, 1.0),
        (2.0, 1.0 + math.sqrt(3)),
    ]
    assert len(centers) == len(expected)
    for c, e in zip(centers, expected):
        assert math.isclose(c[0], e[0], rel_tol=1e-9)
        assert math.isclose(c[1], e[1], rel_tol=1e-9)


def test_pack_hex_top_down_margin():
    centers = pack_hex_top_down(4, 4, 2, margin=1)
    assert centers == [(1.0, 1.0)]


def test_pack_hex_top_down_insufficient():
    assert pack_hex_top_down(1, 1, 2) == []
