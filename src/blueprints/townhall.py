from __future__ import annotations

from ..building import BuildingBlueprint
from ..constants import Color

BLUEPRINT = BuildingBlueprint(
    name="TownHall",
    build_time=0,
    footprint=[(0, 0)],
    glyph="H",
    color=Color.BUILDING,
    wood=0,
    stone=0,
    passable=True,
    unlocked_by_townhall_level=1,
    foundation_wood=0,
    foundation_stone=0,
)
