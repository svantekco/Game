from __future__ import annotations

import sys

from .constants import Color

try:
    from blessed import Terminal
    _HAS_BLESSED = True
except Exception:  # pragma: no cover - fallback if blessed is missing
    import curses
    _HAS_BLESSED = False


class Renderer:
    """Basic terminal renderer using blessed with a curses fallback."""

    COLOR_ATTRS = {
        Color.GRASS: "green",
        Color.TREE: "yellow",
        Color.ROCK: "white",
        Color.WATER: "blue",
        Color.UI: "magenta",
    }

    def __init__(self) -> None:
        if _HAS_BLESSED:
            self.term = Terminal()
            self.use_curses = False
        else:
            self.term = curses.initscr()
            self.use_curses = True

    def clear(self) -> None:
        if self.use_curses:
            self.term.clear()
            self.term.refresh()
        else:
            sys.stdout.write(self.term.clear())
            sys.stdout.flush()

    def draw_grid(
        self, glyphs: list[list[str]], colors: list[list[Color | None]] | None = None
    ) -> None:
        if colors is None:
            colors = [[None for _ in row] for row in glyphs]

        if self.use_curses:
            for y, row in enumerate(glyphs):
                for x, ch in enumerate(row):
                    self.term.addstr(y, x, ch)
            self.term.refresh()
            return

        out: list[str] = []
        for y, row in enumerate(glyphs):
            for x, ch in enumerate(row):
                color = colors[y][x]
                move = self.term.move_xy(x, y)
                if color:
                    attr = self.COLOR_ATTRS.get(color)
                    if attr and hasattr(self.term, attr):
                        out.append(move + getattr(self.term, attr)(ch))
                    else:
                        out.append(move + ch)
                else:
                    out.append(move + ch)
        sys.stdout.write("".join(out))
        sys.stdout.flush()
