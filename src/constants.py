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
