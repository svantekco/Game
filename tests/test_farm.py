from src.game import Game
from src.building import Building


def test_farm_produces_food():
    game = Game(seed=42)
    bp = game.blueprints["Farm"]
    farm = Building(bp, game.townhall_pos)
    farm.progress = bp.build_time
    farm.passable = False
    game.buildings.append(farm)
    game.tick_count = game.tick_rate * 5
    game._produce_food()
    assert game.storage["food"] == 1
