from src.game import Game
from src.constants import Role
from src.villager import Villager


def test_explorer_creates_village():
    created = []
    g = Game(seed=1)
    g.on_new_village = lambda pos: created.append(pos)
    v = Villager(id=99, position=g.townhall_pos, role=Role.EXPLORER)
    v.explore_steps = 0
    g.entities.append(v)
    v.update(g)
    assert created
