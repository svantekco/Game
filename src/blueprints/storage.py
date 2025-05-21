from __future__ import annotations

from ..building import BuildingBlueprint
from ..constants import Color

BLUEPRINT = BuildingBlueprint(
    name="Storage",
    build_time=0,
    footprint=[(0, 0)],
    glyph="S",
    color=Color.BUILDING,
    wood=20,
    stone=20,
    passable=True,
)
