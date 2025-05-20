from enum import Enum, auto

# Map dimensions
# Expand the world to a very large grid.  The map no longer stores all tiles in
# memory at once, so these values can be huge without exhausting RAM.
MAP_WIDTH = 100_000
MAP_HEIGHT = 100_000


class TileType(Enum):
    GRASS = auto()
    TREE = auto()
    ROCK = auto()
    WATER = auto()


# Camera defaults
VIEWPORT_WIDTH = 80
# Height of the UI panel at the bottom of the screen
UI_PANEL_HEIGHT = 10
# Height of the game viewport (excluding UI panel)
VIEWPORT_HEIGHT = 24 - UI_PANEL_HEIGHT
# Y coordinate where the status line is rendered
STATUS_PANEL_Y = VIEWPORT_HEIGHT
# Discrete zoom levels: 1 cell per tile, 2 cells per tile, etc.
ZOOM_LEVELS = [1, 2, 4]
DEFAULT_ZOOM_INDEX = 0

# Game tick rate (ticks per second)
TICK_RATE = 60

# Amount of resources a villager can carry at once
CARRY_CAPACITY = 10

# Minimum number of ticks between villager actions
VILLAGER_ACTION_DELAY = 30

# Maximum combined resources that can be stored
MAX_STORAGE = 100

# Maximum nodes explored during breadth-first searches to avoid hangs on
# extremely large maps.
SEARCH_LIMIT = 10000


class Color(Enum):
    """Logical color identifiers used for rendering."""

    GRASS = auto()
    TREE = auto()
    ROCK = auto()
    WATER = auto()
    PATH = auto()
    BUILDING = auto()
    UI = auto()


class Style(Enum):
    """Text style attributes."""

    NORMAL = auto()
    BOLD = auto()
    UNDERLINE = auto()
