from __future__ import annotations

from ..building import BuildingBlueprint
from ..constants import Color

BLUEPRINT = BuildingBlueprint(
    name="Farm",
    build_time=8,
    footprint=[(0, 0)],
    glyph="f",
    color=Color.BUILDING,
    wood=10,
    stone=5,
)
