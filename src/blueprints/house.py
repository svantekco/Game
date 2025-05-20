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
)
