from __future__ import annotations

from dataclasses import dataclass, field
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
    capacity: int = 0
    efficiency: float = 1.0
    capacity_bonus: int = 0
    # If True the completed building can be walked over
    passable: bool = False
    unlocked_by_townhall_level: int = 1
    foundation_wood: int = 0
    foundation_stone: int = 0


@dataclass
class Building:
    """Instance of a placed building."""

    blueprint: BuildingBlueprint
    position: Tuple[int, int]
    progress: int = 0
    passable: bool = True
    residents: List[int] = field(default_factory=list)
    level: int = 1
    capacity: int = 0
    efficiency: float = 1.0
    builder_id: int | None = None
    construction_stage: str = "complete"

    def __post_init__(self) -> None:
        """Initialise stats from the blueprint."""
        self.capacity = self.blueprint.capacity
        self.efficiency = self.blueprint.efficiency

    # ---------------------------------------------------------------
    def upgrade_cost(self) -> Tuple[int, int]:
        """Return wood and stone cost for the next upgrade."""
        target = self.level + 1
        return (
            self.blueprint.wood * target,
            self.blueprint.stone * target,
        )

    def apply_upgrade(self) -> None:
        """Increase building stats when an upgrade occurs."""
        self.level += 1
        self.capacity += 1
        self.efficiency += 0.1

    def cells(self) -> List[Tuple[int, int]]:
        """World coordinates occupied by this building."""
        return [
            (self.position[0] + dx, self.position[1] + dy)
            for dx, dy in self.blueprint.footprint
        ]

    @property
    def complete(self) -> bool:
        return self.construction_stage == "complete"

    # ------------------------------------------------------------------
    def glyph_for_progress(self) -> tuple[str, Color]:
        """Return a glyph and colour based on construction progress."""

        if self.construction_stage == "complete" or self.blueprint.build_time <= 0:
            return self.blueprint.glyph, self.blueprint.color

        if self.construction_stage == "foundation":
            # Assuming foundation is 25% of total build time
            ratio = self.progress / (self.blueprint.build_time * 0.25)
            if ratio < 0.5:
                glyph = "x"
            else:
                glyph = "X"
            return glyph, Color.RED
        
        if self.construction_stage == "main_construction":
            # Assuming main construction is 75% of total build time
            ratio = self.progress / (self.blueprint.build_time * 0.75)
            if ratio < 1/3:
                glyph = "."
            elif ratio < 2/3:
                glyph = "+"
            else:
                glyph = self.blueprint.glyph.lower()
            return glyph, self.blueprint.color
        
        # Should not happen, but as a fallback
        return self.blueprint.glyph, self.blueprint.color
