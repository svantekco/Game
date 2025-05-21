import random

import src.villager as villager_mod
from src.game import Game


def test_villager_wanders_when_search_fails(monkeypatch):
    game = Game(seed=1)
    vill = game.entities[0]
    start = vill.position

    monkeypatch.setattr(
        villager_mod, "find_nearest_resource", lambda *a, **k: (None, [])
    )
    monkeypatch.setattr(random, "shuffle", lambda x: None)

    vill.update(game)
    assert vill.position != start
