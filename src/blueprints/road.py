from __future__ import annotations

from ..building import BuildingBlueprint
from ..constants import Color

BLUEPRINT = BuildingBlueprint(
    name="Road",
    build_time=1,
    footprint=[(0, 0)],
    glyph="=",
    color=Color.PATH,
    wood=0,
    stone=5,
    passable=True,
    unlocked_by_townhall_level=1,
    foundation_wood=0,
    foundation_stone=1,
)
