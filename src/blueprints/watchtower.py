from __future__ import annotations

from ..building import BuildingBlueprint
from ..constants import Color

BLUEPRINT = BuildingBlueprint(
    name="Watchtower",
    build_time=20,
    footprint=[(0, 0)],
    glyph="T",
    color=Color.BUILDING,
    wood=30,
    stone=5,
)
