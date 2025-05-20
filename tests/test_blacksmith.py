from src.game import Game
from src.building import Building
from src.constants import VILLAGER_ACTION_DELAY


def test_blacksmith_speed_bonus():
    game = Game(seed=42)
    bp = game.blueprints["Blacksmith"]
    pos = (game.townhall_pos[0] + 1, game.townhall_pos[1])
    smith = Building(bp, pos, progress=bp.build_time)
    smith.passable = False
    game.buildings.append(smith)
    vill = game.entities[0]
    vill.position = pos
    delay = vill._apply_tool_bonus(game, VILLAGER_ACTION_DELAY)
    assert delay < VILLAGER_ACTION_DELAY
