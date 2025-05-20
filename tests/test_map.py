import pytest

from src.map import GameMap
from src.pathfinding import find_path


def test_map_connectivity():
    gmap = GameMap(seed=42)
    start = (0, 0)
    goal = (gmap.width // 2, gmap.height // 2)
    path = find_path(start, goal, gmap, [])
    assert path, "no path between corners"
