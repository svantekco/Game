from __future__ import annotations


class World:
    """Simple container for global time and day/night cycle."""

    def __init__(self, tick_rate: int, day_length: int | None = None) -> None:
        self.tick_rate = tick_rate
        self.day_length = day_length or tick_rate * 30
        self.tick_count = 0

    def tick(self) -> None:
        """Advance world time by one tick."""
        self.tick_count += 1

    @property
    def is_night(self) -> bool:
        cycle_pos = self.tick_count % self.day_length
        return cycle_pos >= self.day_length // 2
