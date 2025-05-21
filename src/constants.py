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
VIEWPORT_HEIGHT = 42 - UI_PANEL_HEIGHT
# Y coordinate where the status line is rendered
STATUS_PANEL_Y = VIEWPORT_HEIGHT
# Discrete zoom levels: 1 cell per tile, 2 cells per tile, etc.
ZOOM_LEVELS = [1, 2, 4]
DEFAULT_ZOOM_INDEX = 0

# Game tick rate (ticks per second)
# Increased to speed up the simulation
TICK_RATE = 360

# How often to fully refresh the UI to avoid artefacts
UI_REFRESH_INTERVAL = TICK_RATE * 5  # every 5 seconds

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
    HOUSING_ZONE = auto()
    WORK_ZONE = auto()
    MARKET_ZONE = auto()


class Style(Enum):
    """Text style attributes."""

    NORMAL = auto()
    BOLD = auto()
    UNDERLINE = auto()


class Personality(Enum):
    """Villager personality traits."""

    BRAVE = auto()
    LAZY = auto()
    INDUSTRIOUS = auto()
    SOCIAL = auto()


class Mood(Enum):
    """Villager mood levels."""

    HAPPY = auto()
    NEUTRAL = auto()
    SAD = auto()


class ZoneType(Enum):
    """Designated zones for building placement."""

    HOUSING = auto()
    WORK = auto()
    MARKET = auto()


class LifeStage(Enum):
    """Lifecycle stages for villagers."""

    CHILD = auto()
    ADULT = auto()
    ELDER = auto()
    RETIRED = auto()
