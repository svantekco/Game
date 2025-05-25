import random
import pytest
import src.villager as villager_mod


@pytest.fixture(autouse=True)
def disable_random_wander(monkeypatch):
    monkeypatch.setattr(villager_mod.random, "random", lambda: 1.0)
    yield
