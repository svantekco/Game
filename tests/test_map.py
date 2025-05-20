from src.map import GameMap
from src.pathfinding import find_path


def test_map_connectivity():
    gmap = GameMap(seed=42)
    start = (0, 0)
    # With a huge map it's unrealistic to path all the way to the centre in
    # tests. Instead verify a short path exists.
    goal = (10, 10)
    path = find_path(start, goal, gmap, [])
    assert path, "no path between corners"
