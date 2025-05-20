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
)
