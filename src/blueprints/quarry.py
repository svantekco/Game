from __future__ import annotations

from ..building import BuildingBlueprint
from ..constants import Color

BLUEPRINT = BuildingBlueprint(
    name="Quarry",
    build_time=12,
    footprint=[(0, 0)],
    glyph="Q",
    color=Color.BUILDING,
    wood=10,
    stone=10,
)
