from src.multigame import MultiGame


def test_add_village_limit():
    mg = MultiGame(seed=1)
    for _ in range(10):
        mg._add_village((0, 0))
    assert len(mg.villages) <= 9
