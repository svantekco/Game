import sys
from src.renderer import Renderer
from src.constants import Color, UI_COLOR_RGB


def test_ui_fixed_colour(monkeypatch):
    renderer = Renderer()
    monkeypatch.setattr(renderer.term, "move_xy", lambda x, y: "")

    called = {}

    def fake_color(idx):
        called["idx"] = idx
        return ""

    monkeypatch.setattr(renderer.term.__class__, "color", lambda self, idx: fake_color(idx))

    class Dummy:
        def write(self, s):
            pass

        def flush(self):
            pass

    monkeypatch.setattr(sys, "stdout", Dummy())

    renderer.draw_grid([["X"]], [[Color.UI]])

    expected = Renderer._rgb_to_ansi256(*UI_COLOR_RGB)
    assert called["idx"] == expected


def test_ui_no_colour(monkeypatch):
    renderer = Renderer(use_color=False)
    monkeypatch.setattr(renderer.term, "move_xy", lambda x, y: "")

    called = {}

    def fake_color(idx):
        called["idx"] = idx
        return ""

    monkeypatch.setattr(renderer.term.__class__, "color", lambda self, idx: fake_color(idx))

    class Dummy:
        def write(self, s):
            pass

        def flush(self):
            pass

    monkeypatch.setattr(sys, "stdout", Dummy())

    renderer.draw_grid([["X"]], [[Color.UI]])

    assert "idx" not in called
