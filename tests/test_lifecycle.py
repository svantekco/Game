from src.game import Game
from src.building import Building
from src.constants import LifeStage


def test_aging_transitions():
    game = Game(seed=1)
    vill = game.entities[0]
    assert vill.life_stage is LifeStage.ADULT
    vill.age = 64
    vill.age_one_day(game)
    assert vill.life_stage is LifeStage.ELDER
    vill.age = 79
    vill.age_one_day(game)
    assert vill.life_stage is LifeStage.RETIRED


def test_birth_requires_food_and_housing():
    game = Game(seed=1)
    bp = game.blueprints["House"]
    house = Building(bp, game.townhall_pos)
    house.progress = bp.build_time
    house.passable = False
    game.buildings.append(house)
    game.storage["food"] = 1
    game._handle_births()
    game._process_spawns()
    assert any(v.life_stage is LifeStage.CHILD for v in game.entities)
