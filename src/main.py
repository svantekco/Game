from __future__ import annotations

import time

from .map import GameMap
from .renderer import Renderer
from .camera import Camera
from .constants import Color, TileType, TICK_RATE


def _tile_to_render(tile: TileType) -> tuple[str, Color]:
    """Return a glyph and color for the given tile type."""
    if tile is TileType.GRASS:
        return ".", Color.GRASS
    if tile is TileType.TREE:
        return "T", Color.TREE
    if tile is TileType.ROCK:
        return "R", Color.ROCK
    return "~", Color.WATER


def _render_view(renderer: Renderer, gmap: GameMap, camera: Camera) -> None:
    """Render the portion of the map visible through the camera."""
    glyph_grid: list[list[str]] = []
    color_grid: list[list[Color]] = []

    for ty in range(camera.visible_tiles_y):
        glyph_row: list[str] = []
        color_row: list[Color] = []
        for tx in range(camera.visible_tiles_x):
            wx = camera.x + tx
            wy = camera.y + ty
            tile = gmap.get_tile(wx, wy)
            glyph, color = _tile_to_render(tile.type)
            glyph_row.extend([glyph] * camera.zoom)
            color_row.extend([color] * camera.zoom)
        for _ in range(camera.zoom):
            glyph_grid.append(glyph_row)
            color_grid.append(color_row)

    renderer.clear()
    renderer.draw_grid(glyph_grid, color_grid)


def main() -> None:
    print("Game starting...")
    gmap = GameMap(seed=42)

    renderer = Renderer()
    renderer.clear()

    camera = Camera()

    term = renderer.term
    with term.cbreak(), term.hidden_cursor():
        while True:
            _render_view(renderer, gmap, camera)

            key = term.inkey(timeout=1 / TICK_RATE)
            if not key:
                continue

            if key.code == term.KEY_LEFT:
                camera.move(-1, 0, gmap.width, gmap.height)
            elif key.code == term.KEY_RIGHT:
                camera.move(1, 0, gmap.width, gmap.height)
            elif key.code == term.KEY_UP:
                camera.move(0, -1, gmap.width, gmap.height)
            elif key.code == term.KEY_DOWN:
                camera.move(0, 1, gmap.width, gmap.height)
            elif key == "+":
                camera.zoom_in()
                camera.move(0, 0, gmap.width, gmap.height)
            elif key == "-":
                camera.zoom_out()
                camera.move(0, 0, gmap.width, gmap.height)
            elif key.lower() == "q":
                break

            time.sleep(0)


if __name__ == "__main__":
    main()
