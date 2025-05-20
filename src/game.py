# Game loop and state management
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

from .constants import CARRY_CAPACITY, TileType
from .pathfinding import find_nearest_resource, find_path

from .map import GameMap
from .renderer import Renderer
from .camera import Camera


@dataclass
class Villager:
    """Simple villager entity."""

    id: int
    position: Tuple[int, int]
    state: str = "idle"
    inventory: Dict[str, int] = field(default_factory=lambda: {"wood": 0, "stone": 0})
    carrying_capacity: int = CARRY_CAPACITY
    target_path: List[Tuple[int, int]] = field(default_factory=list)
    target_resource: Optional[Tuple[int, int]] = None
    resource_type: Optional[TileType] = None

    # ---------------------------------------------------------------
    def is_full(self) -> bool:
        return sum(self.inventory.values()) >= self.carrying_capacity

    def update(self, game: "Game") -> None:
        """Finite state machine handling villager behaviour."""
        if self.state == "idle":
            # Find nearest tree for now
            pos, path = find_nearest_resource(self.position, TileType.TREE, game.map, game.buildings)
            if pos is None:
                return
            self.resource_type = TileType.TREE
            self.target_resource = pos
            self.target_path = path[1:]
            self.state = "gather"
            return

        if self.state == "gather":
            if self.target_path:
                self.position = self.target_path.pop(0)
                return
            if self.target_resource and self.position == self.target_resource:
                tile = game.map.get_tile(*self.position)
                gained = tile.extract(1)
                self.inventory["wood"] += gained
                if self.is_full() or tile.resource_amount == 0:
                    self.state = "deliver"
                    self.target_path = []
            return

        if self.state == "deliver":
            if not self.target_path:
                path = find_path(self.position, game.storage_pos, game.map, game.buildings)
                self.target_path = path[1:]
            if self.target_path:
                self.position = self.target_path.pop(0)
                return
            if self.position == game.storage_pos:
                game.adjust_storage("wood", self.inventory.get("wood", 0))
                self.inventory["wood"] = 0
                self.state = "idle"

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
        # Global resource storage
        self.storage: Dict[str, int] = {"wood": 0, "stone": 0}
        # Storage location (centre of the map for now)
        self.storage_pos: Tuple[int, int] = (self.map.width // 2, self.map.height // 2)

        self.renderer = Renderer()
        self.camera = Camera()

        # Create a single villager at the storage location as a demo
        self.entities.append(Villager(id=1, position=self.storage_pos))

        self.running = False
        self.tick_rate = 1.0  # ticks per second

    # --- Resource Helpers ---------------------------------------------
    def adjust_storage(self, resource: str, amount: int) -> None:
        """Add or remove resources from global storage."""
        self.storage[resource] = self.storage.get(resource, 0) + amount
        if self.storage[resource] < 0:
            self.storage[resource] = 0

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

        # Update entities
        for vill in self.entities:
            vill.update(self)

    def render(self) -> None:
        """Draw the current game state."""
        self.renderer.render_game(self.map, self.camera, self.entities)
