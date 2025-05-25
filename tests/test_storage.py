def test_storage_capacity_increases_after_completion():
    from src.game import Game
    from src.building import Building

    game = Game(seed=1)
    vill = game.entities[0]
    bp = game.blueprints["Storage"]
    bp.build_time = 1
    pos = (vill.x + 1, vill.y)
    b = Building(bp, pos)
    game.buildings.append(b)
    game.build_queue.append(b)
    game._assign_builder(b)

    prev = game.storage_capacity
    vill.state = "build"
    vill.target_building = b
    vill.target_path = []
    vill.update(game)

    assert b.complete
    assert game.storage_capacity == prev + bp.capacity_bonus

def test_assign_builder_immediate_storage_adds_capacity():
    from src.game import Game
    from src.building import Building

    game = Game(seed=1)
    vill = game.entities[0]
    bp = game.blueprints["Storage"]
    pos = (vill.x + 1, vill.y)
    b = Building(bp, pos, progress=bp.build_time)
    game.buildings.append(b)
    prev = game.storage_capacity
    game._assign_builder(b)
    assert game.storage_capacity == prev + bp.capacity_bonus

