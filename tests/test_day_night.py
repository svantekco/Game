from src.world import World
from src.game import Game


def test_world_day_night_toggle():
    world = World(tick_rate=10, day_length=24)
    world.tick_count = 23
    assert world.is_night
    world.tick_count = 6
    assert not world.is_night


def test_world_time_of_day():
    world = World(tick_rate=10, day_length=24)
    world.tick_count = world.day_length // 2
    assert world.time_of_day == "12:00"


def test_villager_slow_at_night():
    game = Game(seed=1)
    vill = game.entities[0]
    base = 10
    game.world.tick_count = game.world.day_length // 2
    day_delay = vill._action_delay(game, base)
    game.world.tick_count = game.world.day_length * 23 // 24
    night_delay = vill._action_delay(game, base)
    # A small random variation is applied to action delays, so allow some
    # tolerance when comparing day and night values.
    assert night_delay >= int(day_delay * 1.2)
