from src.game import Game
from src.building import Building


def test_villager_stays_adjacent_while_building():
    game = Game(seed=42)
    vill = game.entities[0]
    bp = game.blueprints["House"]
    pos = (game.townhall_pos[0] + 2, game.townhall_pos[1])
    building = Building(bp, pos)
    game.buildings.append(building)
    game.build_queue.append(building)
    game._assign_builder(building)

    building_positions = []
    started = False
    for _ in range(bp.build_time + 5):
        vill.update(game)
        if building.progress > 0:
            started = True
        if started:
            building_positions.append(vill.position)
        if building.complete:
            break
    assert building.complete
    for p in building_positions:
        assert abs(p[0] - pos[0]) + abs(p[1] - pos[1]) == 1
