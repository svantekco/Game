from src.game import Game
from src.constants import TileType


def test_quarry_site_near_rocks():
    game = Game(seed=42)
    bp = game.blueprints["Quarry"]
    pos = game.find_quarry_site(bp)
    assert pos is not None
    assert game._count_resource_nearby(pos, TileType.ROCK, radius=2) > 0
