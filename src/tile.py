from dataclasses import dataclass
from .constants import TileType


@dataclass
class Tile:
    """Represents a single map tile."""

    type: TileType
    resource_amount: int = 0
    passable: bool = True

    def __repr__(self) -> str:
        return (
            f"Tile(type={self.type}, res={self.resource_amount}, "
            f"passable={self.passable})"
        )
