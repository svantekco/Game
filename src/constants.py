from enum import Enum, auto

# Map dimensions
MAP_WIDTH = 1000
MAP_HEIGHT = 1000

class TileType(Enum):
    GRASS = auto()
    TREE = auto()
    ROCK = auto()
    WATER = auto()

# Camera defaults
VIEWPORT_WIDTH = 80
VIEWPORT_HEIGHT = 24
# Discrete zoom levels: 1 cell per tile, 2 cells per tile, etc.
ZOOM_LEVELS = [1, 2, 4]
DEFAULT_ZOOM_INDEX = 0

# Game tick rate (ticks per second)
TICK_RATE = 60

# Amount of resources a villager can carry at once
CARRY_CAPACITY = 10


class Color(Enum):
    """Logical color identifiers used for rendering."""

    GRASS = auto()
    TREE = auto()
    ROCK = auto()
    WATER = auto()
    UI = auto()


class Style(Enum):
    """Text style attributes."""

    NORMAL = auto()
    BOLD = auto()
    UNDERLINE = auto()
