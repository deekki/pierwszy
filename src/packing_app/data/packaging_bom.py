from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List


class PackagingLevel(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"
    AUXILIARY = "auxiliary"


@dataclass(frozen=True)
class PackagingComponent:
    name: str
    mass_kg: float
    quantity: int = 1
    level: PackagingLevel = PackagingLevel.PRIMARY

    def total_mass(self) -> float:
        return self.mass_kg * self.quantity


@dataclass
class PackagingBOM:
    components: List[PackagingComponent] = field(default_factory=list)

    def add(self, component: PackagingComponent) -> None:
        self.components.append(component)

    def extend(self, components: Iterable[PackagingComponent]) -> None:
        self.components.extend(list(components))

    def total_mass(self, level: PackagingLevel | None = None) -> float:
        if level is None:
            return sum(component.total_mass() for component in self.components)
        return sum(
            component.total_mass()
            for component in self.components
            if component.level == level
        )

    def mass_breakdown(self) -> Dict[PackagingLevel, float]:
        breakdown: Dict[PackagingLevel, float] = {
            PackagingLevel.PRIMARY: 0.0,
            PackagingLevel.SECONDARY: 0.0,
            PackagingLevel.TERTIARY: 0.0,
            PackagingLevel.AUXILIARY: 0.0,
        }
        for component in self.components:
            breakdown[component.level] += component.total_mass()
        return breakdown
