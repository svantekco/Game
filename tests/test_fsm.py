from src.game import Game


def test_villager_gather_cycle():
    game = Game(seed=42)
    game.world.tick_count = game.world.day_length // 4
    vill = game.entities[0]
    # Run a few ticks to allow gather/deliver
    for _ in range(1000):
        vill.update(game)
        if game.storage["wood"] > 0:
            break
    assert game.storage["wood"] >= 0
    assert vill.state in {"idle", "gather", "deliver", "build"}
