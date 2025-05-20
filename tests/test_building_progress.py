from src.building import Building, BuildingBlueprint
from src.constants import Color
from src.renderer import Renderer
from src.camera import Camera
from src.map import GameMap


def test_glyph_for_progress():
    bp = BuildingBlueprint(
        name="Test",
        build_time=10,
        footprint=[(0, 0)],
        glyph="X",
        color=Color.BUILDING,
    )
    b = Building(bp, (0, 0))
    assert b.glyph_for_progress()[0] == "."
    b.progress = 5
    assert b.glyph_for_progress()[0] == "+"
    b.progress = 9
    assert b.glyph_for_progress()[0] == "x"
    b.progress = 10
    assert b.glyph_for_progress()[0] == "X"


def test_renderer_uses_progress(monkeypatch):
    gmap = GameMap(seed=1)
    renderer = Renderer()
    camera = Camera()
    camera.set_zoom_level(0)
    camera.x = 0
    camera.y = 0
    bp = BuildingBlueprint(
        name="Test",
        build_time=5,
        footprint=[(0, 0)],
        glyph="B",
        color=Color.BUILDING,
    )
    building = Building(bp, (0, 0))

    def fake_glyph_for_progress():
        return "Z", Color.UI

    building.glyph_for_progress = fake_glyph_for_progress

    captured = {}

    def fake_draw(g, c):
        captured["glyphs"] = g
        captured["colors"] = c

    monkeypatch.setattr(renderer, "draw_grid", fake_draw)

    renderer.render_game(gmap, camera, [], [building], detailed=False)

    assert captured["glyphs"][0][0] == "Z"
    assert captured["colors"][0][0] == Color.UI
