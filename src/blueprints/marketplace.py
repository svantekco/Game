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
)
