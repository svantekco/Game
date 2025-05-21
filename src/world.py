from __future__ import annotations


class World:
    """Simple container for global time and day/night cycle."""

    def __init__(self, tick_rate: int, day_length: int | None = None) -> None:
        self.tick_rate = tick_rate
        # Default day length slowed down so in-game time progresses
        # at a more relaxed pace (roughly four times slower than before)
        self.day_length = day_length or tick_rate * 24
        self.tick_count = 0
        self.day = 0

    def tick(self) -> None:
        """Advance world time by one tick."""
        prev = self.tick_count // self.day_length
        self.tick_count += 1
        if self.tick_count // self.day_length > prev:
            self.day += 1

    @property
    def is_night(self) -> bool:
        """Return True if time is between 00:00 and 03:00."""
        hour = int(self.day_fraction * 24)
        return hour < 3

    @property
    def time_of_day(self) -> str:
        """Return the current time of day as ``HH:MM``."""
        cycle_pos = self.tick_count % self.day_length
        day_fraction = cycle_pos / self.day_length
        hours = int(day_fraction * 24)
        minutes = int((day_fraction * 24 - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"

    @property
    def day_fraction(self) -> float:
        """Current time of day as a value in ``[0, 1]``."""
        return (self.tick_count % self.day_length) / self.day_length
