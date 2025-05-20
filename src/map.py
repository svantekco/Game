import random
from typing import List

from .constants import MAP_WIDTH, MAP_HEIGHT, TileType
from .tile import Tile


class GameMap:
    """Represents the game world as a grid of tiles."""

    def __init__(self, seed: int | None = None) -> None:
        self.width = MAP_WIDTH
        self.height = MAP_HEIGHT
        self._rand = random.Random(seed)
        self.grid: List[List[Tile]] = [
            [self._generate_tile() for _ in range(self.width)]
            for _ in range(self.height)
        ]

    def _generate_tile(self) -> Tile:
        tile_type = self._rand.choices(
            [TileType.GRASS, TileType.TREE, TileType.ROCK, TileType.WATER],
            weights=[0.5, 0.2, 0.2, 0.1],
        )[0]
        if tile_type is TileType.GRASS:
            return Tile(tile_type, resource_amount=0, passable=True)
        if tile_type is TileType.TREE:
            amt = self._rand.randint(5, 20)
            return Tile(tile_type, resource_amount=amt, passable=False)
        if tile_type is TileType.ROCK:
            amt = self._rand.randint(3, 10)
            return Tile(tile_type, resource_amount=amt, passable=False)
        # Water
        return Tile(tile_type, resource_amount=0, passable=False)

    def get_tile(self, x: int, y: int) -> Tile:
        return self.grid[y][x]
