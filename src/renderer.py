from __future__ import annotations

import sys
import time
import logging
from typing import TYPE_CHECKING

from .constants import Color, TileType, STATUS_PANEL_Y, Mood, UI_COLOR_RGB
from .filters import apply_lighting, day_night_filter, zone_filter

logger = logging.getLogger(__name__)

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

    UI_RGB = UI_COLOR_RGB
    COLOR_ATTRS = {
        Color.GRASS: "green",
        Color.TREE: "yellow",
        Color.ROCK: "white",
        Color.WATER: "blue",
        Color.PATH: "cyan",
        Color.BUILDING: "magenta",
        # UI colour is handled separately to avoid lighting effects.
        # Zone overlays use a bold variant of the base tile colour so
        # the underlying terrain remains recognisable while still
        # highlighting the designated zone.
        Color.HOUSING_ZONE: "bold_green",
        Color.WORK_ZONE: "bold_yellow",
        Color.MARKET_ZONE: "bold_blue",
    }

    def __init__(self) -> None:
        if _HAS_BLESSED:
            self.term = Terminal()
            if not self.term.does_styling:
                # Force colour output when blessed detects a non-tty stream.
                # Some environments mis-report TTY capabilities which causes
                # ``does_styling`` to be ``False`` even though ANSI colours are
                # supported.  Recreate the ``Terminal`` with ``force_styling``
                # enabled so the renderer always emits colour escape codes.
                self.term = Terminal(force_styling=True)
            self.use_curses = False
        else:
            self.term = curses.initscr()
            self.use_curses = True

        # Track previously rendered frame so we can update only changed
        # positions. Each element mirrors the glyph/color grid passed to
        # ``draw_grid``.
        self._last_glyphs: list[list[str]] | None = None
        self._last_colors: list[list[object | None]] | None = None
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
        self, glyphs: list[list[str]], colors: list[list[object | None]] | None = None
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

            def apply_color(text: str, color: object | None) -> str:
                if color is None:
                    return text
                if isinstance(color, tuple):
                    if hasattr(self.term, "color_rgb"):
                        return self.term.color_rgb(*color) + text
                    return text
                if color is Color.UI:
                    if hasattr(self.term, "color_rgb"):
                        return self.term.color_rgb(*self.UI_RGB) + text
                    return text
                attr = self.COLOR_ATTRS.get(color)
                if attr and hasattr(self.term, attr):
                    return getattr(self.term, attr)(text)
                return text

            out: list[str] = []
            for y, row in enumerate(glyphs):
                color_row = colors[y]
                if not full_redraw and self._last_glyphs is not None:
                    if (
                        row == self._last_glyphs[y]
                        and color_row == self._last_colors[y]
                    ):
                        continue

                segments: list[str] = []
                start = 0
                current_color = color_row[0]
                for x, color in enumerate(color_row):
                    if color != current_color:
                        segment = "".join(row[start:x])
                        segments.append(apply_color(segment, current_color))
                        start = x
                        current_color = color
                segment = "".join(row[start:])
                segments.append(apply_color(segment, current_color))
                out.append(self.term.move_xy(0, y) + "".join(segments))

            sys.stdout.write("".join(out))
            sys.stdout.flush()

        # Store frame for diffing next draw
        self._last_glyphs = [row.copy() for row in glyphs]
        self._last_colors = [row.copy() for row in colors]

    # ------------------------------------------------------------------
    def _tile_to_render(self, tile: TileType, detailed: bool) -> str:
        """Return a glyph for the given tile type."""
        if detailed:
            if tile is TileType.GRASS:
                glyph = "."
            elif tile is TileType.TREE:
                glyph = "t"
            elif tile is TileType.ROCK:
                glyph = "^"
            else:
                glyph = "~"
        else:
            if tile is TileType.GRASS:
                glyph = "G"
            elif tile is TileType.TREE:
                glyph = "T"
            elif tile is TileType.ROCK:
                glyph = "R"
            else:
                glyph = "W"

        return glyph

    def render_game(
        self,
        gmap: "GameMap",
        camera: "Camera",
        villagers: list["Villager"],
        buildings: list[object] | None = None,
        detailed: bool = False,
        *,
        is_night: bool = False,
        day_fraction: float = 0.0,
        filters: list | None = None,
        reserved: set[tuple[int, int]] | None = None,
    ) -> None:
        """Render the visible portion of the map with villagers and buildings."""

        if buildings is None:
            buildings = []
        if filters is None:
            filters = [zone_filter, day_night_filter]
        if reserved is None:
            reserved = set()

        start_total = time.perf_counter()
        lighting_time = 0.0
        base_time = 0.0
        building_time = 0.0
        path_time = 0.0
        villager_time = 0.0
        draw_time = 0.0

        glyph_grid: list[list[str]] = []
        color_grid: list[list[object]] = []

        t0 = time.perf_counter()
        for ty in range(camera.visible_tiles_y):
            glyph_row: list[str] = []
            color_row: list[object] = []
            for tx in range(camera.visible_tiles_x):
                wx = camera.x + tx
                wy = camera.y + ty
                tile = gmap.get_tile(wx, wy)
                glyph = self._tile_to_render(tile.type, detailed)
                t0 = time.perf_counter()
                color = apply_lighting(tile, day_fraction, filters)
                if (wx, wy) in reserved:
                    color = tuple(min(255, int(c * 1.3)) for c in color)
                lighting_time += time.perf_counter() - t0
                if is_night:
                    glyph = glyph.lower()

                glyph_row.extend([glyph] * camera.zoom)
                color_row.extend([color] * camera.zoom)
            for _ in range(camera.zoom):
                glyph_grid.append(glyph_row.copy())
                color_grid.append(color_row.copy())
        base_time = time.perf_counter() - t0

        t0 = time.perf_counter()
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

                    if b.blueprint.name == "Road" and getattr(b, "complete", False):
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
        building_time = time.perf_counter() - t0

        t0 = time.perf_counter()
        # Overlay villager paths first so the villager glyphs appear on top
        for vill in villagers:
            path = getattr(vill, "target_path", [])
            for px, py in path[:-1]:
                sx, sy = camera.world_to_screen(px, py)
                if 0 <= sy < len(glyph_grid) and 0 <= sx < len(glyph_grid[0]):
                    glyph_grid[sy][sx] = "\xb7"  # middle dot character
                    color_grid[sy][sx] = Color.PATH
        path_time = time.perf_counter() - t0

        t0 = time.perf_counter()
        # Overlay villagers
        for vill in villagers:
            sx, sy = camera.world_to_screen(vill.x, vill.y)
            if 0 <= sy < len(glyph_grid) and 0 <= sx < len(glyph_grid[0]):
                glyph_grid[sy][sx] = "z" if getattr(vill, "asleep", False) else "@"
                color_grid[sy][sx] = Color.UI
                mood_char = {
                    Mood.HAPPY: "^",
                    Mood.NEUTRAL: "~",
                    Mood.SAD: "v",
                }.get(vill.mood, "~")
                if sx + 1 < len(glyph_grid[0]):
                    glyph_grid[sy][sx + 1] = mood_char
                    color_grid[sy][sx + 1] = Color.UI
        villager_time = time.perf_counter() - t0

        t0 = time.perf_counter()
        self.draw_grid(glyph_grid, color_grid)
        draw_time = time.perf_counter() - t0

        total_time = (time.perf_counter() - start_total) * 1000
        logger.debug(
            "render_game took %.2f ms (tiles %.2f ms, buildings %.2f ms, paths %.2f ms,"
            " villagers %.2f ms, draw %.2f ms, lighting %.2f ms)",
            total_time,
            base_time * 1000,
            building_time * 1000,
            path_time * 1000,
            villager_time * 1000,
            draw_time * 1000,
            lighting_time * 1000,
        )

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
            prefix = (
                self.term.color_rgb(*self.UI_RGB)
                if hasattr(self.term, "color_rgb")
                else ""
            )
            sys.stdout.write(self.term.move_xy(0, STATUS_PANEL_Y) + prefix + line)
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
                prefix = (
                    self.term.color_rgb(*self.UI_RGB)
                    if hasattr(self.term, "color_rgb")
                    else ""
                )
                sys.stdout.write(self.term.move_xy(0, y) + prefix + line)
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
                prefix = (
                    self.term.color_rgb(*self.UI_RGB)
                    if hasattr(self.term, "color_rgb")
                    else ""
                )
                sys.stdout.write(self.term.move_xy(0, y) + prefix + line)
        if self.use_curses:
            self.term.refresh()
        else:
            sys.stdout.flush()
