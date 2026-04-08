import math

from packing_app.core.empty_space import (
    calculate_empty_space,
    volume_oblong_mm3,
    volume_oval_mm3,
    volume_round_mm3,
)


def test_round_volume_matches_sphere_formula():
    diameter = 10.0
    expected = (4.0 / 3.0) * math.pi * 5.0**3
    assert volume_round_mm3(diameter) == expected


def test_oval_volume_matches_ellipsoid_formula():
    length, width, height = 12.0, 8.0, 6.0
    expected = math.pi * length * width * height / 6.0
    assert volume_oval_mm3(length, width, height) == expected


def test_oblong_volume_uses_non_negative_cylinder_part_when_length_is_shorter_than_diameter():
    total_length = 8.0
    diameter = 10.0
    expected = (4.0 / 3.0) * math.pi * 5.0**3
    assert volume_oblong_mm3(total_length, diameter) == expected


def test_calculate_empty_space_returns_expected_percentages_and_free_volume():
    result = calculate_empty_space(unit_volume_mm3=1000.0, quantity=20, container_volume_cc=50.0)

    assert result.volume_unit_cc == 1.0
    assert result.total_volume_cc == 20.0
    assert result.fill_percent == 40.0
    assert result.empty_percent == 60.0
    assert result.free_volume_cc == 30.0


def test_calculate_empty_space_allows_overfill_values():
    result = calculate_empty_space(unit_volume_mm3=2000.0, quantity=40, container_volume_cc=50.0)

    assert result.total_volume_cc == 80.0
    assert result.fill_percent == 160.0
    assert result.empty_percent == -60.0
    assert result.free_volume_cc == -30.0
