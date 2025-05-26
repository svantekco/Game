from __future__ import annotations

from ..building import BuildingBlueprint
from ..constants import Color

BLUEPRINT = BuildingBlueprint(
    name="Blacksmith",
    build_time=25,
    footprint=[(0, 0)],
    glyph="B",
    color=Color.BUILDING,
    wood=20,
    stone=30,
    unlocked_by_townhall_level=3,
    foundation_wood=5,
    foundation_stone=10,
)
