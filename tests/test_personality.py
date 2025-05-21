from src.game import Game
from src.constants import Personality, Mood


def test_villager_has_personality_and_mood():
    game = Game(seed=42)
    vill = game.entities[0]
    assert vill.personality in list(Personality)
    assert vill.mood is Mood.NEUTRAL
