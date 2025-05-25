from src.game import Game
from src.building import Building


def test_villager_sleeps_and_wakes():
    game = Game(seed=1)
    vill = game.entities[0]
    bp = game.blueprints["House"]
    home = Building(bp, (vill.x + 1, vill.y), progress=bp.build_time)
    home.passable = True
    game.buildings.append(home)
    game._assign_home(vill)
    assert vill.home == home.position

    game.world.tick_count = game.world.day_length * 23 // 24
    vill.update(game)
    assert vill.state == "sleep"
    for _ in range(10):
        vill.update(game)
        if vill.asleep:
            break
    assert vill.asleep
    assert vill.thought(game) == "Sleeping"

    game.world.tick_count = game.world.day_length // 4
    vill.update(game)
    assert not vill.asleep
    assert vill.state != "sleep"
