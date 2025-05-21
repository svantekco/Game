import random
from dataclasses import dataclass
from typing import Dict, Tuple

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
        self._rand = random.Random(seed)
        # Tiles are generated lazily and cached in this dict
        self._tiles: Dict[Tuple[int, int], Tile] = {}
        # Map of coordinates to zone type
        self._zones: Dict[Tuple[int, int], ZoneType] = {}
        # Ensure origin is always passable for deterministic tests
        self._tiles[(0, 0)] = Tile(TileType.GRASS, 0, True)

    def _hash(self, x: int, y: int) -> float:
        """Deterministic hash used for noise generation."""
        return random.Random((x * 73856093) ^ (y * 19349663) ^ self.seed).random()

    def _lerp(self, a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    def _value_noise(self, x: int, y: int, scale: int = 25) -> float:
        """Simple value noise based on deterministic hashes."""
        x0 = x // scale
        y0 = y // scale
        fx = (x % scale) / scale
        fy = (y % scale) / scale

        n00 = self._hash(x0, y0)
        n10 = self._hash(x0 + 1, y0)
        n01 = self._hash(x0, y0 + 1)
        n11 = self._hash(x0 + 1, y0 + 1)

        nx0 = self._lerp(n00, n10, fx)
        nx1 = self._lerp(n01, n11, fx)
        return self._lerp(nx0, nx1, fy)

    def _generate_tile(self, x: int, y: int) -> Tile:
        noise = self._value_noise(x, y)
        if noise < 0.5:
            return Tile(TileType.GRASS, resource_amount=0, passable=True)
        if noise < 0.65:
            decorative = self._hash(x + 1, y + 1) < 0.1
            amt = 0 if decorative else 100
            # Trees should be traversable so villagers can gather wood
            return Tile(TileType.TREE, resource_amount=amt, passable=True)
        if noise < 0.98:
            # Allow walking onto rocks for mining
            return Tile(TileType.ROCK, resource_amount=100, passable=True)
        return Tile(TileType.WATER, resource_amount=0, passable=False)

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
