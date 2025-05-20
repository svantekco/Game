import random
from typing import Dict, Tuple

from .constants import MAP_WIDTH, MAP_HEIGHT, TileType
from .tile import Tile


class GameMap:
    """Represents the game world as a grid of tiles."""

    def __init__(self, seed: int | None = None) -> None:
        self.width = MAP_WIDTH
        self.height = MAP_HEIGHT
        self.seed = seed or 0
        self._rand = random.Random(seed)
        # Tiles are generated lazily and cached in this dict
        self._tiles: Dict[Tuple[int, int], Tile] = {}

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
            amt = 5 + int(self._hash(x, y) * 15)
            return Tile(TileType.TREE, resource_amount=amt, passable=False)
        if noise < 0.8:
            amt = 3 + int(self._hash(x, y + 1) * 8)
            return Tile(TileType.ROCK, resource_amount=amt, passable=False)
        return Tile(TileType.WATER, resource_amount=0, passable=False)

    def get_tile(self, x: int, y: int) -> Tile:
        """Return the tile at ``x,y``, generating it if necessary."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError("tile coordinates out of bounds")
        key = (x, y)
        if key not in self._tiles:
            self._tiles[key] = self._generate_tile(x, y)
        return self._tiles[key]
