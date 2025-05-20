from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .constants import Color


@dataclass
class BuildingBlueprint:
    """Template for constructing buildings."""

    name: str
    build_time: int
    footprint: List[Tuple[int, int]]
    glyph: str
    color: Color
    wood: int = 0
    stone: int = 0


@dataclass
class Building:
    """Instance of a placed building."""

    blueprint: BuildingBlueprint
    position: Tuple[int, int]
    progress: int = 0
    passable: bool = True

    def cells(self) -> List[Tuple[int, int]]:
        """World coordinates occupied by this building."""
        return [
            (self.position[0] + dx, self.position[1] + dy)
            for dx, dy in self.blueprint.footprint
        ]

    @property
    def complete(self) -> bool:
        return self.progress >= self.blueprint.build_time
