from src.map import GameMap
from src.pathfinding import find_path


def test_find_path_valid_steps():
    gmap = GameMap(seed=42)
    start = (0, 0)
    goal = (5, 0)
    path = find_path(start, goal, gmap, [])
    assert path[0] == start and path[-1] == goal
    for a, b in zip(path, path[1:]):
        dx = abs(a[0] - b[0]) + abs(a[1] - b[1])
        assert dx == 1
