from __future__ import annotations

from ..building import BuildingBlueprint
from ..constants import Color

BLUEPRINT = BuildingBlueprint(
    name="House",
    build_time=15,
    footprint=[(0, 0)],
    glyph="h",
    color=Color.BUILDING,
    wood=15,
    stone=0,
    capacity=2,
    unlocked_by_townhall_level=1,
    foundation_wood=5,
    foundation_stone=0,
)
