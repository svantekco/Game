from src.blueprints import BLUEPRINTS
from src.game import Game
from src.constants import ZoneType


def test_marketplace_blueprint_loaded():
    assert "Marketplace" in BLUEPRINTS
    bp = BLUEPRINTS["Marketplace"]
    assert bp.glyph == "M"


def test_marketplace_planned_in_progression():
    game = Game(seed=1)
    bp = game.blueprints["Marketplace"]
    # Ensure resources are available
    game.storage["wood"] = bp.wood
    game.storage["stone"] = bp.stone
    assert ZoneType.MARKET in game.zones
    game._plan_townhall_progress()
    assert any(b.blueprint.name == "Marketplace" for b in game.build_queue)
