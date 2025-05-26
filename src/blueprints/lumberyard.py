from __future__ import annotations

from ..building import BuildingBlueprint
from ..constants import Color

BLUEPRINT = BuildingBlueprint(
    name="Lumberyard",
    build_time=10,
    footprint=[(0, 0)],
    glyph="L",
    color=Color.BUILDING,
    wood=10,
    stone=0,
    unlocked_by_townhall_level=1,
    foundation_wood=2,
    foundation_stone=0,
)
