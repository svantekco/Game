from types import SimpleNamespace

from src.game import Game


def test_progress_over_time():
    game = Game(seed=1)
    # replace the renderer terminal with a dummy object so the game loop
    # doesn't require an actual terminal device during tests
    game.renderer.term = SimpleNamespace(getch=lambda: -1)
    game.renderer.use_curses = True

    prev_storage = dict(game.storage)
    prev_buildings = len(game.buildings)
    log = []

    for tick in range(1, 5001):
        game.update()
        if tick % 500 == 0:
            current_storage = dict(game.storage)
            current_buildings = len(game.buildings)
            log.append((tick, current_storage.copy(), current_buildings))
            assert (
                current_storage != prev_storage or current_buildings != prev_buildings
            ), f"No progress at tick {tick}; log so far: {log}"
            prev_storage = current_storage
            prev_buildings = current_buildings
