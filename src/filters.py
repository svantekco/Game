# Lighting and colour filter pipeline
from __future__ import annotations

from typing import Callable, Iterable, Tuple, Dict
import logging
import math

from .constants import TileType, ZoneType
from .tile import Tile

ColorRGB = Tuple[int, int, int]
Filter = Callable[[ColorRGB, Tile, float], ColorRGB]

# Cache for lighting results. Keyed by tile type, zone, rounded day fraction and
# filter functions. This avoids recalculating colours for identical conditions.
_CACHE: Dict[tuple[TileType, ZoneType | None, int, tuple[Filter, ...]], ColorRGB] = {}
_MAX_CACHE = 2048
logger = logging.getLogger(__name__)

# Base colours for tiles ----------------------------------------------
BASE_TILE_COLOURS: dict[TileType, ColorRGB] = {
    TileType.GRASS: (34, 139, 34),
    TileType.TREE: (0, 100, 0),
    TileType.ROCK: (128, 128, 128),
    TileType.WATER: (0, 0, 255),
}

# Zone tint colours
ZONE_TINTS: dict[ZoneType, ColorRGB] = {
    ZoneType.HOUSING: (50, 200, 50),
    ZoneType.WORK: (200, 200, 50),
    ZoneType.MARKET: (50, 50, 200),
}


# Pipeline -------------------------------------------------------------


def apply_lighting(
    tile: Tile, day_fraction: float, filters: Iterable[Filter]
) -> ColorRGB:
    """Return final colour for ``tile`` after applying ``filters``.

    Results are cached based on tile type, zone and day fraction (rounded to two
    decimal places) so repeated frames are faster.
    """
    day_key = int(day_fraction * 100)
    key = (tile.type, tile.zone, day_key, tuple(filters))
    if key in _CACHE:
        return _CACHE[key]

    color = BASE_TILE_COLOURS.get(tile.type, (255, 255, 255))
    for f in filters:
        color = f(color, tile, day_fraction)

    if len(_CACHE) >= _MAX_CACHE:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = color
    return color


# Built-in filters ----------------------------------------------------


def day_night_filter(color: ColorRGB, tile: Tile, day_fraction: float) -> ColorRGB:
    """Darken or lighten ``color`` based on ``day_fraction``.

    ``day_fraction`` should be in ``[0,1]`` where ``0`` is midnight and ``0.5``
    is noon.
    """
    brightness = 0.3 + 0.7 * math.sin(math.pi * day_fraction)
    r, g, b = color
    return (int(r * brightness), int(g * brightness), int(b * brightness))


def zone_filter(color: ColorRGB, tile: Tile, day_fraction: float) -> ColorRGB:
    """Tint tiles based on their zone."""
    if tile.zone is None:
        return color
    tint = ZONE_TINTS.get(tile.zone)
    if tint is None:
        return color
    blend = 0.5
    r = int(color[0] * (1 - blend) + tint[0] * blend)
    g = int(color[1] * (1 - blend) + tint[1] * blend)
    b = int(color[2] * (1 - blend) + tint[2] * blend)
    return (r, g, b)
