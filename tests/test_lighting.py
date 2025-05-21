from src.filters import apply_lighting, day_night_filter, zone_filter, ColorRGB, BASE_TILE_COLOURS
from src.tile import Tile
from src.constants import TileType, ZoneType


def test_day_night_filter_darkens():
    colour = (100, 100, 100)
    result = day_night_filter(colour, Tile(TileType.GRASS), 0.0)
    assert result == (30, 30, 30)


def test_zone_filter_tints():
    colour = (100, 100, 100)
    tile = Tile(TileType.GRASS, zone=ZoneType.HOUSING)
    result = zone_filter(colour, tile, 0.0)
    assert result == (75, 150, 75)


def test_apply_lighting_combines():
    tile = Tile(TileType.GRASS, zone=ZoneType.HOUSING)
    result = apply_lighting(tile, 0.5, [zone_filter, day_night_filter])
    assert result == (42, 169, 42)
