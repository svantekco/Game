from src.map import GameMap
from src.pathfinding import find_path, find_nearest_resource, find_path_hierarchical
from src.constants import TileType
from src.blueprints import BLUEPRINTS
from src.building import Building


def test_find_path_valid_steps():
    gmap = GameMap(seed=42)
    start = (0, 0)
    goal = (5, 0)
    path = find_path(start, goal, gmap, [])
    assert path[0] == start and path[-1] == goal
    for a, b in zip(path, path[1:]):
        dx = abs(a[0] - b[0]) + abs(a[1] - b[1])
        assert dx == 1


def test_find_nearest_resource_prefers_roads():
    gmap = GameMap(seed=1)
    road_bp = BLUEPRINTS["Road"]
    roads = [
        Building(road_bp, (0, 1), progress=road_bp.build_time),
        Building(road_bp, (0, 2), progress=road_bp.build_time),
        Building(road_bp, (0, 3), progress=road_bp.build_time),
    ]
    for r in roads:
        r.passable = True

    gmap.get_tile(2, 0).type = TileType.ROCK
    gmap.get_tile(2, 0).resource_amount = 100
    gmap.get_tile(0, 3).type = TileType.ROCK
    gmap.get_tile(0, 3).resource_amount = 100

    pos, _ = find_nearest_resource((0, 0), TileType.ROCK, gmap, roads, search_limit=20)
    assert pos == (0, 3)


def test_hierarchical_path_returns_to_goal():
    gmap = GameMap(seed=2)
    start = (0, 0)
    goal = (70, 0)
    path = find_path_hierarchical(start, goal, gmap, [], coarse_distance=20, step=4)
    assert path[0] == start and path[-1] == goal
    # ensure path uses only adjacent steps
    for a, b in zip(path, path[1:]):
        dx = abs(a[0] - b[0]) + abs(a[1] - b[1])
        assert dx == 1
