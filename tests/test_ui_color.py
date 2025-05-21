import sys
from src.renderer import Renderer
from src.constants import Color, UI_COLOR_RGB


def test_ui_fixed_colour(monkeypatch):
    renderer = Renderer()
    monkeypatch.setattr(renderer.term, "move_xy", lambda x, y: "")

    called = {}

    def fake_color_rgb(r, g, b):
        called["rgb"] = (r, g, b)
        return ""

    monkeypatch.setattr(renderer.term, "color_rgb", fake_color_rgb)

    class Dummy:
        def write(self, s):
            pass

        def flush(self):
            pass

    monkeypatch.setattr(sys, "stdout", Dummy())

    renderer.draw_grid([["X"]], [[Color.UI]])

    assert called["rgb"] == UI_COLOR_RGB
