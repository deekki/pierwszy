from dataclasses import dataclass

from .units import MM


@dataclass
class Carton:
    """Simple carton dimensions."""

    width: MM
    length: MM
    height: MM = 0.0


@dataclass
class Pallet:
    """Simple pallet dimensions."""

    width: MM
    length: MM
    height: MM = 0.0
