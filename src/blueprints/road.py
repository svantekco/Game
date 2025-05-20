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
)
