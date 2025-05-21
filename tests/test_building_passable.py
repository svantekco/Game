from src.game import Game
from src.blueprints import BLUEPRINTS
from src.building import Building


def test_road_remains_passable_after_built():
    game = Game(seed=1)
    vill = game.entities[0]
    bp = BLUEPRINTS["Road"]
    b = Building(bp, (vill.x + 1, vill.y), progress=bp.build_time - 1)
    game.buildings.append(b)
    game.build_queue.append(b)

    vill.state = "build"
    vill.target_building = b
    vill.target_path = []
    # positioned adjacent, so update will build
    vill.update(game)
    assert b.complete
    assert b.passable is True
