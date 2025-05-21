from src.world import World
from src.game import Game
from src.building import Building


def test_world_day_night_toggle():
    world = World(tick_rate=10, day_length=20)
    assert not world.is_night
    for _ in range(10):
        world.tick()
    assert world.is_night


def test_villager_sleeps_at_night():
    game = Game(seed=1)
    vill = game.entities[0]
    bp = game.blueprints["House"]
    house = Building(bp, vill.position)
    house.progress = bp.build_time
    house.passable = True
    game.buildings.append(house)
    house.residents.append(vill.id)
    vill.home = house.position
    game.world.tick_count = game.world.day_length // 2 + 1
    vill.update(game)
    assert vill.asleep
    assert vill.state == "sleeping"
