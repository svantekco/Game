from dataclasses import dataclass
from .constants import TileType, ZoneType


@dataclass
class Tile:
    """Represents a single map tile."""

    type: TileType
    resource_amount: int = 0
    passable: bool = True
    zone: ZoneType | None = None

    def __repr__(self) -> str:
        return (
            f"Tile(type={self.type}, res={self.resource_amount}, "
            f"passable={self.passable})"
        )

    # New helper -------------------------------------------------------
    def extract(self, amount: int) -> int:
        """Remove up to ``amount`` resource units from this tile."""
        if amount <= 0 or self.resource_amount <= 0:
            return 0
        removed = min(self.resource_amount, amount)
        self.resource_amount -= removed
        # Trees/Rocks disappear when depleted
        if self.resource_amount == 0 and self.type in (TileType.TREE, TileType.ROCK):
            self.type = TileType.GRASS
            self.passable = True
        return removed
