from __future__ import annotations

from ..building import BuildingBlueprint
from ..constants import Color

BLUEPRINT = BuildingBlueprint(
    name="Marketplace",
    build_time=18,
    footprint=[(0, 0)],
    glyph="M",
    color=Color.BUILDING,
    wood=25,
    stone=20,
    unlocked_by_townhall_level=2,
    foundation_wood=5,
    foundation_stone=5,
)
