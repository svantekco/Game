from __future__ import annotations

import random
import time
from typing import List

from .game import Game


class MultiGame:
    """Manage multiple independent villages."""

    def __init__(self, seed: int | None = None, preview: bool = False) -> None:
        self.villages: List[Game] = []
        first = Game(seed=seed, preview=preview)
        first.on_new_village = self._add_village
        first.running = True
        self.villages.append(first)
        self.active = 0
        self.running = False

    def _add_village(self, pos: tuple[int, int]) -> None:
        if len(self.villages) >= 9:
            return
        seed = random.randint(0, 1_000_000)
        g = Game(seed=seed)
        g.on_new_village = self._add_village
        g.running = True
        self.villages.append(g)

    def run(self, show_fps: bool = False) -> None:
        self.running = True
        term = self.villages[0].renderer.term
        if self.villages[0].renderer.use_curses:
            import curses

            curses.cbreak()
            curses.noecho()
            term.nodelay(True)
            try:
                last = time.perf_counter()
                while self.running and any(
                    v.running is not False for v in self.villages
                ):
                    start = time.perf_counter()
                    ch = term.getch()
                    key = ch if ch != -1 else None
                    self._process_key(key)
                    for idx, g in enumerate(self.villages):
                        g.update(key if idx == self.active else None)
                    self.villages[self.active].render()
                    last = self._sleep(last, start)
            finally:
                term.nodelay(False)
                curses.nocbreak()
                curses.echo()
                curses.endwin()
        else:
            with term.cbreak(), term.hidden_cursor():
                last = time.perf_counter()
                while self.running and any(
                    v.running is not False for v in self.villages
                ):
                    start = time.perf_counter()
                    key = term.inkey(timeout=0)
                    self._process_key(key)
                    for idx, g in enumerate(self.villages):
                        g.update(key if idx == self.active else None)
                    self.villages[self.active].render()
                    last = self._sleep(last, start)

    def _process_key(self, key: int | str | None) -> None:
        if key in (ord("q"), "q"):
            self.running = False
            for g in self.villages:
                g.running = False
        if key:
            if isinstance(key, int):
                if ord("1") <= key <= ord("9"):
                    self.active = min(len(self.villages) - 1, key - ord("1"))
            else:
                if key in "123456789":
                    self.active = min(len(self.villages) - 1, int(key) - 1)

    def _sleep(self, last: float, start: float) -> float:
        current = time.perf_counter()
        for g in self.villages:
            g.last_tick_ms = (time.perf_counter() - start) * 1000
            g.current_fps = 1 / max(1e-6, current - last)
        sleep = max(0, (1 / self.villages[0].tick_rate) - (time.perf_counter() - start))
        time.sleep(sleep)
        return current
