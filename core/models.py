from dataclasses import dataclass

@dataclass
class Carton:
    width: float
    length: float
    height: float

@dataclass
class Pallet:
    name: str
    width: float
    length: float
    height: float

@dataclass
class Container:
    width: float
    length: float
    height: float
