from src.game import Game
from src.constants import Role, LifeStage, TileType


def test_roles_assigned_when_population_reaches_five():
    game = Game(seed=1)
    for _ in range(4):
        game._spawn_villager(game.townhall_pos, age=18, stage=LifeStage.ADULT)
    game._update_roles()
    roles = {v.role for v in game.entities}
    assert Role.BUILDER in roles
    assert Role.WOODCUTTER in roles
    assert Role.MINER in roles
    assert Role.ROAD_PLANNER in roles


def test_woodcutter_gathers_wood():
    game = Game(seed=1)
    for _ in range(4):
        game._spawn_villager(game.townhall_pos, age=18, stage=LifeStage.ADULT)
    game._update_roles()
    woodcutter = next(v for v in game.entities if v.role is Role.WOODCUTTER)
    job = game.dispatch_job(woodcutter)
    assert job.type == "gather"
    assert job.payload == TileType.TREE
