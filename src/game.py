# Game loop and state management
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .map import GameMap
from .renderer import Renderer
from .camera import Camera


@dataclass
class Villager:
    """Simple villager entity."""

    id: int
    position: Tuple[int, int]
    state: str = "idle"
    inventory: Dict[str, int] = field(default_factory=dict)
    target_path: List[Tuple[int, int]] = field(default_factory=list)

    @property
    def x(self) -> int:
        return self.position[0]

    @property
    def y(self) -> int:
        return self.position[1]


class Game:
    """Owns game state and runs the main loop."""

    def __init__(self, seed: int | None = None) -> None:
        self.map = GameMap(seed=seed)
        self.entities: List[Villager] = []
        self.buildings: List[object] = []
        self.storage: Dict[str, int] = {}

        self.renderer = Renderer()
        self.camera = Camera()

        # Create a single villager in the center of the map as a demo
        center = (self.map.width // 2, self.map.height // 2)
        self.entities.append(Villager(id=1, position=center))

        self.running = False
        self.tick_rate = 1.0  # ticks per second

    # --- Game Loop -----------------------------------------------------
    def run(self) -> None:
        """Run the main loop until quit."""
        self.running = True
        term = self.renderer.term
        if self.renderer.use_curses:
            import curses

            curses.cbreak()
            curses.noecho()
            try:
                while self.running:
                    self.update()
                    self.render()
                    time.sleep(1 / self.tick_rate)
            finally:
                curses.nocbreak()
                curses.echo()
                curses.endwin()
        else:
            with term.cbreak(), term.hidden_cursor():
                while self.running:
                    self.update()
                    self.render()
                    time.sleep(1 / self.tick_rate)

    def update(self) -> None:
        """Process input and update world state."""
        term = self.renderer.term
        key = term.inkey(timeout=0)
        if key:
            if key.code == term.KEY_LEFT:
                self.camera.move(-1, 0, self.map.width, self.map.height)
            elif key.code == term.KEY_RIGHT:
                self.camera.move(1, 0, self.map.width, self.map.height)
            elif key.code == term.KEY_UP:
                self.camera.move(0, -1, self.map.width, self.map.height)
            elif key.code == term.KEY_DOWN:
                self.camera.move(0, 1, self.map.width, self.map.height)
            elif key == '+':
                self.camera.zoom_in()
                self.camera.move(0, 0, self.map.width, self.map.height)
            elif key == '-':
                self.camera.zoom_out()
                self.camera.move(0, 0, self.map.width, self.map.height)
            elif key.lower() == 'q':
                self.running = False

    def render(self) -> None:
        """Draw the current game state."""
        self.renderer.render_game(self.map, self.camera, self.entities)
