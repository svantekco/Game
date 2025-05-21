from src.world import World
from src.game import Game
from src.building import Building


def test_world_day_night_toggle():
    world = World(tick_rate=10, day_length=24)
    assert world.is_night
    for _ in range(3):
        world.tick()
    assert not world.is_night


def test_world_time_of_day():
    world = World(tick_rate=10, day_length=24)
    world.tick_count = world.day_length // 2
    assert world.time_of_day == "12:00"


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
    game.world.tick_count = game.world.day_length // 24
    vill.update(game)
    assert vill.asleep
    assert vill.state == "sleeping"
