from src.blueprints import BLUEPRINTS
from src.game import Game
from src.building import Building


def test_watchtower_blueprint_loaded():
    assert "Watchtower" in BLUEPRINTS
    bp = BLUEPRINTS["Watchtower"]
    assert bp.glyph == "T"


def test_watchtower_increases_search_limit():
    game = Game(seed=42)
    base_limit = game.get_search_limit()
    bp = game.blueprints["Watchtower"]
    b = Building(bp, (game.townhall_pos[0] + 2, game.townhall_pos[1]))
    b.progress = bp.build_time
    b.passable = False
    game.buildings.append(b)
    assert game.get_search_limit() > base_limit
