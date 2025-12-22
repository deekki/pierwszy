from dataclasses import dataclass


@dataclass
class Carton:
    """Simple carton dimensions."""

    width: float
    length: float
    height: float = 0.0


@dataclass
class Pallet:
    """Simple pallet dimensions."""

    width: float
    length: float
    height: float = 0.0
