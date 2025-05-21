from dataclasses import dataclass
from typing import Dict, Tuple

from .terrain import TerrainGenerator

from .constants import MAP_WIDTH, MAP_HEIGHT, TileType, ZoneType
from .tile import Tile


@dataclass
class Zone:
    """Simple rectangular zone."""

    type: ZoneType
    x: int
    y: int
    width: int
    height: int


class GameMap:
    """Represents the game world as a grid of tiles."""

    def __init__(self, seed: int | None = None) -> None:
        self.width = MAP_WIDTH
        self.height = MAP_HEIGHT
        self.seed = seed or 0
        self.terrain = TerrainGenerator(self.width, self.height, self.seed)
        self.precomputed_clusters = self.terrain.precomputed_clusters
        # Tiles are generated lazily and cached in this dict
        self._tiles: Dict[Tuple[int, int], Tile] = {}
        # Map of coordinates to zone type
        self._zones: Dict[Tuple[int, int], ZoneType] = {}
        # Ensure origin is always passable for deterministic tests
        self._tiles[(0, 0)] = Tile(TileType.GRASS, 0, True)
        self._clear_start_area()

    def _clear_start_area(self) -> None:
        """Ensure a small patch around the origin is walkable."""
        for x in range(3):
            for y in range(3):
                self._tiles[(x, y)] = Tile(TileType.GRASS, 0, True)

    def _generate_tile(self, x: int, y: int) -> Tile:
        t, amt, passable = self.terrain.tile_at(x, y)
        return Tile(t, resource_amount=amt, passable=passable)

    def get_tile(self, x: int, y: int) -> Tile:
        """Return the tile at ``x,y``, generating it if necessary."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError("tile coordinates out of bounds")
        key = (x, y)
        if key not in self._tiles:
            self._tiles[key] = self._generate_tile(x, y)
        tile = self._tiles[key]
        tile.zone = self._zones.get(key)
        return tile

    def add_zone(self, zone: "Zone") -> None:
        """Mark a rectangular area as belonging to ``zone``."""
        for x in range(zone.x, zone.x + zone.width):
            for y in range(zone.y, zone.y + zone.height):
                if 0 <= x < self.width and 0 <= y < self.height:
                    self._zones[(x, y)] = zone.type
