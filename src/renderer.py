from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from .constants import Color, TileType, STATUS_PANEL_Y

if TYPE_CHECKING:  # pragma: no cover - imports for type hints only
    from .map import GameMap
    from .camera import Camera
    from .game import Villager

try:
    from blessed import Terminal

    _HAS_BLESSED = True
except Exception:  # pragma: no cover - fallback if blessed is missing
    import curses

    _HAS_BLESSED = False

if TYPE_CHECKING:  # pragma: no cover - import types for checking only
    from .game import Villager, Camera
    from .map import GameMap


class Renderer:
    """Basic terminal renderer using blessed with a curses fallback."""

    COLOR_ATTRS = {
        Color.GRASS: "green",
        Color.TREE: "yellow",
        Color.ROCK: "white",
        Color.WATER: "blue",
        Color.PATH: "cyan",
        Color.BUILDING: "magenta",
        Color.UI: "white",
    }

    def __init__(self) -> None:
        if _HAS_BLESSED:
            self.term = Terminal()
            self.use_curses = False
        else:
            self.term = curses.initscr()
            self.use_curses = True

        # Track previously rendered frame so we can update only changed
        # positions. Each element mirrors the glyph/color grid passed to
        # ``draw_grid``.
        self._last_glyphs: list[list[str]] | None = None
        self._last_colors: list[list[Color | None]] | None = None
        self._last_size: tuple[int, int] = (0, 0)

    def clear(self) -> None:
        if self.use_curses:
            self.term.clear()
            self.term.refresh()
        else:
            sys.stdout.write(self.term.clear())
            sys.stdout.flush()
        # Reset diff tracking since the screen is now blank
        self._last_glyphs = None
        self._last_colors = None

    def draw_grid(
        self, glyphs: list[list[str]], colors: list[list[Color | None]] | None = None
    ) -> None:
        if colors is None:
            colors = [[None for _ in row] for row in glyphs]

        height = len(glyphs)
        width = len(glyphs[0]) if height else 0

        size = (width, height)
        full_redraw = size != self._last_size or self._last_glyphs is None
        if full_redraw:
            # If the grid size changed (e.g., zoom level), clear the screen and
            # redraw everything.
            self.clear()
            self._last_size = size

        if self.use_curses:
            for y, row in enumerate(glyphs):
                for x, ch in enumerate(row):
                    if (
                        full_redraw
                        or self._last_glyphs[y][x] != ch
                        or self._last_colors[y][x] != colors[y][x]
                    ):
                        self.term.addstr(y, x, ch)
            self.term.refresh()
        else:
            out: list[str] = []
            for y, row in enumerate(glyphs):
                for x, ch in enumerate(row):
                    if (
                        full_redraw
                        or self._last_glyphs[y][x] != ch
                        or self._last_colors[y][x] != colors[y][x]
                    ):
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

        # Store frame for diffing next draw
        self._last_glyphs = [row.copy() for row in glyphs]
        self._last_colors = [row.copy() for row in colors]

    # ------------------------------------------------------------------
    def _tile_to_render(self, tile: TileType, detailed: bool) -> tuple[str, Color]:
        """Return a glyph and color for the given tile type."""
        if detailed:
            if tile is TileType.GRASS:
                return ".", Color.GRASS
            if tile is TileType.TREE:
                return "t", Color.TREE
            if tile is TileType.ROCK:
                return "^", Color.ROCK
            return "~", Color.WATER
        else:
            if tile is TileType.GRASS:
                return "G", Color.GRASS
            if tile is TileType.TREE:
                return "T", Color.TREE
            if tile is TileType.ROCK:
                return "R", Color.ROCK
            return "W", Color.WATER

    def render_game(
        self,
        gmap: "GameMap",
        camera: "Camera",
        villagers: list["Villager"],
        buildings: list[object] | None = None,
        detailed: bool = False,
    ) -> None:
        """Render the visible portion of the map with villagers and buildings."""

        if buildings is None:
            buildings = []
        glyph_grid: list[list[str]] = []
        color_grid: list[list[Color]] = []

        for ty in range(camera.visible_tiles_y):
            glyph_row: list[str] = []
            color_row: list[Color] = []
            for tx in range(camera.visible_tiles_x):
                wx = camera.x + tx
                wy = camera.y + ty
                tile = gmap.get_tile(wx, wy)
                glyph, color = self._tile_to_render(tile.type, detailed)
                glyph_row.extend([glyph] * camera.zoom)
                color_row.extend([color] * camera.zoom)
            for _ in range(camera.zoom):
                glyph_grid.append(glyph_row.copy())
                color_grid.append(color_row.copy())

        # Overlay buildings
        for b in buildings:
            render_fn = getattr(b, "glyph_for_progress", None)
            for bx, by in getattr(
                b, "cells", lambda: [(b.position[0], b.position[1])]
            )():
                sx, sy = camera.world_to_screen(bx, by)
                if 0 <= sy < len(glyph_grid) and 0 <= sx < len(glyph_grid[0]):
                    if callable(render_fn):
                        glyph, color = render_fn()
                    else:
                        glyph, color = b.blueprint.glyph, b.blueprint.color

                    if (
                        b.blueprint.name == "Road"
                        and getattr(b, "complete", False)
                    ):
                        n = any(
                            nb.position == (bx, by - 1)
                            and nb.blueprint.name == "Road"
                            and nb.complete
                            for nb in buildings
                        )
                        s = any(
                            nb.position == (bx, by + 1)
                            and nb.blueprint.name == "Road"
                            and nb.complete
                            for nb in buildings
                        )
                        w = any(
                            nb.position == (bx - 1, by)
                            and nb.blueprint.name == "Road"
                            and nb.complete
                            for nb in buildings
                        )
                        e = any(
                            nb.position == (bx + 1, by)
                            and nb.blueprint.name == "Road"
                            and nb.complete
                            for nb in buildings
                        )
                        if (n or s) and not (w or e):
                            glyph = "|"
                        elif (w or e) and not (n or s):
                            glyph = "-"
                        else:
                            glyph = "+"

                    glyph_grid[sy][sx] = glyph
                    color_grid[sy][sx] = color

        # Overlay villager paths first so the villager glyphs appear on top
        for vill in villagers:
            path = getattr(vill, "target_path", [])
            for px, py in path[:-1]:
                sx, sy = camera.world_to_screen(px, py)
                if 0 <= sy < len(glyph_grid) and 0 <= sx < len(glyph_grid[0]):
                    glyph_grid[sy][sx] = "\xb7"  # middle dot character
                    color_grid[sy][sx] = Color.PATH

        # Overlay villagers
        for vill in villagers:
            sx, sy = camera.world_to_screen(vill.x, vill.y)
            if 0 <= sy < len(glyph_grid) and 0 <= sx < len(glyph_grid[0]):
                glyph_grid[sy][sx] = "@"
                color_grid[sy][sx] = Color.UI

        self.draw_grid(glyph_grid, color_grid)

    def render_status(self, text: str) -> None:
        """Render a status line at the bottom of the screen."""
        if self.use_curses:
            height, width = self.term.getmaxyx()
        else:
            width = self.term.width

        line = text.ljust(width)

        if self.use_curses:
            self.term.addstr(STATUS_PANEL_Y, 0, line[:width])
            self.term.refresh()
        else:
            sys.stdout.write(self.term.move_xy(0, STATUS_PANEL_Y) + line)
            sys.stdout.flush()

    def render_help(self, lines: list[str], start_y: int = 0) -> None:
        """Render help text starting at ``start_y``."""
        if self.use_curses:
            _, width = self.term.getmaxyx()
        else:
            width = self.term.width

        for idx, line in enumerate(lines):
            y = start_y + idx
            line = line.ljust(width)
            if self.use_curses:
                self.term.addstr(y, 0, line[:width])
            else:
                sys.stdout.write(self.term.move_xy(0, y) + line)
        if self.use_curses:
            self.term.refresh()
        else:
            sys.stdout.flush()

    def render_overlay(self, lines: list[str], start_y: int = 0) -> None:
        """Render generic overlay lines starting at ``start_y``."""
        if self.use_curses:
            _, width = self.term.getmaxyx()
        else:
            width = self.term.width

        for idx, line in enumerate(lines):
            y = start_y + idx
            line = line.ljust(width)
            if self.use_curses:
                self.term.addstr(y, 0, line[:width])
            else:
                sys.stdout.write(self.term.move_xy(0, y) + line)
        if self.use_curses:
            self.term.refresh()
        else:
            sys.stdout.flush()
