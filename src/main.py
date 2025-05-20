from .map import GameMap
from .renderer import Renderer
from .constants import Color, TileType


def main() -> None:
    print("Game starting...")
    gmap = GameMap(seed=42)

    renderer = Renderer()
    renderer.clear()

    width, height = 40, 20
    glyph_grid: list[list[str]] = []
    color_grid: list[list[Color]] = []
    for y in range(height):
        glyph_row: list[str] = []
        color_row: list[Color] = []
        for x in range(width):
            tile = gmap.get_tile(x, y)
            if tile.type is TileType.GRASS:
                glyph_row.append(".")
                color_row.append(Color.GRASS)
            elif tile.type is TileType.TREE:
                glyph_row.append("T")
                color_row.append(Color.TREE)
            elif tile.type is TileType.ROCK:
                glyph_row.append("R")
                color_row.append(Color.ROCK)
            else:
                glyph_row.append("~")
                color_row.append(Color.WATER)
        glyph_grid.append(glyph_row)
        color_grid.append(color_row)

    renderer.draw_grid(glyph_grid, color_grid)


if __name__ == "__main__":
    main()
