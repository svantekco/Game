from __future__ import annotations

import sys

from .constants import Color, TileType

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

    # ------------------------------------------------------------------
    def _tile_to_render(self, tile: TileType) -> tuple[str, Color]:
        """Return a glyph and color for the given tile type."""
        if tile is TileType.GRASS:
            return ".", Color.GRASS
        if tile is TileType.TREE:
            return "T", Color.TREE
        if tile is TileType.ROCK:
            return "R", Color.ROCK
        return "~", Color.WATER

    def render_game(
        self, gmap: "GameMap", camera: "Camera", villagers: list["Villager"]
    ) -> None:
        """Render the visible portion of the map with villagers overlaid."""
        glyph_grid: list[list[str]] = []
        color_grid: list[list[Color]] = []

        for ty in range(camera.visible_tiles_y):
            glyph_row: list[str] = []
            color_row: list[Color] = []
            for tx in range(camera.visible_tiles_x):
                wx = camera.x + tx
                wy = camera.y + ty
                tile = gmap.get_tile(wx, wy)
                glyph, color = self._tile_to_render(tile.type)
                glyph_row.extend([glyph] * camera.zoom)
                color_row.extend([color] * camera.zoom)
            for _ in range(camera.zoom):
                glyph_grid.append(glyph_row.copy())
                color_grid.append(color_row.copy())

        # Overlay villager paths first so the villager glyphs appear on top
        for vill in villagers:
            for px, py in getattr(vill, "target_path", []):
                sx, sy = camera.world_to_screen(px, py)
                if 0 <= sy < len(glyph_grid) and 0 <= sx < len(glyph_grid[0]):
                    glyph_grid[sy][sx] = "\xb7"  # middle dot character
                    color_grid[sy][sx] = Color.UI

        # Overlay villagers
        for vill in villagers:
            sx, sy = camera.world_to_screen(vill.x, vill.y)
            if 0 <= sy < len(glyph_grid) and 0 <= sx < len(glyph_grid[0]):
                glyph_grid[sy][sx] = "@"
                color_grid[sy][sx] = Color.UI

        self.clear()
        self.draw_grid(glyph_grid, color_grid)
