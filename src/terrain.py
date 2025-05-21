from __future__ import annotations

import random
from typing import Dict, List, Tuple

from .constants import MAP_WIDTH, MAP_HEIGHT, TileType


class TerrainGenerator:
    """Generate biomes and resource clusters using layered noise."""

    def __init__(
        self, width: int = MAP_WIDTH, height: int = MAP_HEIGHT, seed: int = 0
    ) -> None:
        self.width = width
        self.height = height
        self.seed = seed
        self._rand = random.Random(seed)
        self.precomputed_clusters: Dict[TileType, List[Tuple[int, int]]] = {
            TileType.TREE: [],
            TileType.ROCK: [],
        }
        # Generate a few random cluster centres for resources
        self._init_clusters()

    # --- Noise helpers -------------------------------------------------
    def _hash(self, x: int, y: int) -> float:
        return random.Random((x * 92837111) ^ (y * 689287499) ^ self.seed).random()

    def _lerp(self, a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    def _value_noise(self, x: int, y: int, scale: int = 50) -> float:
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

    # --- Public API ----------------------------------------------------
    def tile_at(self, x: int, y: int) -> Tuple[TileType, int, bool]:
        """Return terrain at ``x,y``."""
        elevation = self._value_noise(x, y, scale=100)
        moisture = self._value_noise(x + 1000, y + 1000, scale=100)
        if elevation < 0.3:
            return TileType.WATER, 0, False
        if elevation > 0.8:
            return TileType.ROCK, 100, True
        if moisture > 0.6:
            amt = 100 if self._hash(x + 1, y + 1) > 0.2 else 0
            return TileType.TREE, amt, True
        return TileType.GRASS, 0, True

    def _init_clusters(self) -> None:
        """Populate ``precomputed_clusters`` with random centres."""
        count = 50
        for _ in range(count):
            x = self._rand.randint(0, self.width - 1)
            y = self._rand.randint(0, self.height - 1)
            t, amt, _ = self.tile_at(x, y)
            if t in (TileType.TREE, TileType.ROCK) and amt > 0:
                self.precomputed_clusters[t].append((x, y))

    def preview(self, scale: int = 1000) -> List[str]:
        """Return a coarse preview of the map."""
        rows: List[str] = []
        for y in range(0, self.height, scale):
            row = []
            for x in range(0, self.width, scale):
                t, _, _ = self.tile_at(x, y)
                if t is TileType.WATER:
                    row.append("~")
                elif t is TileType.ROCK:
                    row.append("^")
                elif t is TileType.TREE:
                    row.append("T")
                else:
                    row.append(".")
            rows.append("".join(row))
        return rows
