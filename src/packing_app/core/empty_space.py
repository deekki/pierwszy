from __future__ import annotations

import math
from dataclasses import dataclass


MM3_IN_CC = 1000.0


@dataclass(frozen=True)
class EmptySpaceResult:
    """Wyniki obliczeń dla zakładki pustej przestrzeni pojemnika."""

    volume_unit_mm3: float
    volume_unit_cc: float
    total_volume_cc: float
    fill_percent: float
    empty_percent: float
    free_volume_cc: float



def volume_round_mm3(diameter_mm: float) -> float:
    """Objętość kuli na podstawie średnicy (mm^3)."""
    radius = diameter_mm / 2.0
    return (4.0 / 3.0) * math.pi * radius**3



def volume_oval_mm3(length_mm: float, width_mm: float, height_mm: float) -> float:
    """Objętość elipsoidy 3D na podstawie długości, szerokości i wysokości (mm^3)."""
    return math.pi * length_mm * width_mm * height_mm / 6.0



def volume_oblong_mm3(total_length_mm: float, diameter_mm: float) -> float:
    """Objętość kapsułki (walec + dwie półkule) w mm^3."""
    radius = diameter_mm / 2.0
    cylinder_length = max(total_length_mm - diameter_mm, 0.0)
    cylinder_volume = math.pi * radius**2 * cylinder_length
    sphere_volume = (4.0 / 3.0) * math.pi * radius**3
    return cylinder_volume + sphere_volume



def calculate_empty_space(
    *,
    unit_volume_mm3: float,
    quantity: int,
    container_volume_cc: float,
) -> EmptySpaceResult:
    """Oblicza zajętość i pustą przestrzeń pojemnika dla zadanej liczby sztuk."""
    volume_unit_cc = unit_volume_mm3 / MM3_IN_CC
    total_volume_cc = volume_unit_cc * quantity
    fill_percent = (total_volume_cc / container_volume_cc) * 100.0
    empty_percent = 100.0 - fill_percent
    free_volume_cc = container_volume_cc - total_volume_cc
    return EmptySpaceResult(
        volume_unit_mm3=unit_volume_mm3,
        volume_unit_cc=volume_unit_cc,
        total_volume_cc=total_volume_cc,
        fill_percent=fill_percent,
        empty_percent=empty_percent,
        free_volume_cc=free_volume_cc,
    )
