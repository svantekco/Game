# Game loop and state management
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

from .constants import (
    CARRY_CAPACITY,
    TileType,
    Color,
    ZOOM_LEVELS,
    TICK_RATE,
    VILLAGER_ACTION_DELAY,
    MAX_STORAGE,
)
from .pathfinding import find_nearest_resource, find_path
from .building import BuildingBlueprint, Building

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
    target_building: Optional[Building] = None
    cooldown: int = 0

    # ---------------------------------------------------------------
    def is_full(self) -> bool:
        return sum(self.inventory.values()) >= self.carrying_capacity

    def update(self, game: "Game") -> None:
        """Finite state machine handling villager behaviour."""
        if self.cooldown > 0:
            self.cooldown -= 1
            return
        if self.state == "idle":
            job = game.dispatch_job()
            if not job:
                return
            if job.type == "gather":
                pos, path = find_nearest_resource(
                    self.position, TileType.TREE, game.map, game.buildings
                )
                if pos is None:
                    return
                self.resource_type = TileType.TREE
                self.target_resource = pos
                self.target_path = path[1:]
                self.state = "gather"
                return
            if job.type == "build":
                self.target_building = job.payload
                path = find_path(
                    self.position,
                    self.target_building.position,
                    game.map,
                    game.buildings,
                )
                self.target_path = path[1:]
                self.state = "build"
                return

        if self.state == "gather":
            if self.target_path:
                self.position = self.target_path.pop(0)
                self.cooldown = VILLAGER_ACTION_DELAY
                return
            if self.target_resource and self.position == self.target_resource:
                tile = game.map.get_tile(*self.position)
                gained = tile.extract(1)
                self.inventory["wood"] += gained
                self.cooldown = VILLAGER_ACTION_DELAY
                if self.is_full() or tile.resource_amount == 0:
                    self.state = "deliver"
                    self.target_path = []
            return

        if self.state == "deliver":
            if not self.target_path:
                path = find_path(
                    self.position, game.storage_pos, game.map, game.buildings
                )
                self.target_path = path[1:]
            if self.target_path:
                self.position = self.target_path.pop(0)
                self.cooldown = VILLAGER_ACTION_DELAY
                return
            if self.position == game.storage_pos:
                game.adjust_storage("wood", self.inventory.get("wood", 0))
                self.inventory["wood"] = 0
                self.cooldown = VILLAGER_ACTION_DELAY
                self.state = "idle"

        if self.state == "build":
            if self.target_path:
                self.position = self.target_path.pop(0)
                self.cooldown = VILLAGER_ACTION_DELAY
                return
            if self.target_building and self.position == self.target_building.position:
                self.target_building.progress += 1
                self.cooldown = VILLAGER_ACTION_DELAY
                if self.target_building.complete:
                    self.target_building.passable = False
                    if self.target_building in game.build_queue:
                        game.build_queue.remove(self.target_building)
                    if self.target_building.blueprint.name == "House":
                        game.schedule_spawn(self.target_building.position)
                self.state = "idle"

    @property
    def x(self) -> int:
        return self.position[0]

    @property
    def y(self) -> int:
        return self.position[1]


@dataclass
class Job:
    """Simple job descriptor used by the dispatcher."""

    type: str  # "gather" or "build"
    payload: object | None = None


class Game:
    """Owns game state and runs the main loop."""

    def __init__(self, seed: int | None = None) -> None:
        self.map = GameMap(seed=seed)
        self.entities: List[Villager] = []
        self.buildings: List[Building] = []
        self.build_queue: List[Building] = []
        self.jobs: List[Job] = []
        self.wood_threshold = 60
        self.house_threshold = 50
        self.next_entity_id = 2
        self.pending_spawns: List[Tuple[int, Tuple[int, int]]] = []

        # Predefined blueprints
        self.blueprints: Dict[str, BuildingBlueprint] = {
            "TownHall": BuildingBlueprint(
                name="TownHall",
                cost=0,
                footprint=[(0, 0)],
                glyph="H",
                color=Color.BUILDING,
            ),
            "Lumberyard": BuildingBlueprint(
                name="Lumberyard",
                cost=10,
                footprint=[(0, 0)],
                glyph="L",
                color=Color.BUILDING,
            ),
            "House": BuildingBlueprint(
                name="House",
                cost=15,
                footprint=[(0, 0)],
                glyph="h",
                color=Color.BUILDING,
            ),
            "Storage": BuildingBlueprint(
                name="Storage",
                cost=0,
                footprint=[(0, 0)],
                glyph="S",
                color=Color.BUILDING,
            ),
        }
        # Global resource storage
        self.storage: Dict[str, int] = {"wood": 0, "stone": 0}
        self.storage_capacity = MAX_STORAGE

        # Place Town Hall at the starting location
        self.townhall_pos: Tuple[int, int] = self._find_start_pos()
        townhall = Building(self.blueprints["TownHall"], self.townhall_pos, progress=0)
        townhall.progress = townhall.blueprint.cost
        townhall.passable = True
        self.buildings.append(townhall)

        # Place initial Storage building 5 tiles east of the Town Hall
        candidate = (self.townhall_pos[0] + 5, self.townhall_pos[1])
        self.storage_pos = self._find_nearest_passable(candidate)
        storage = Building(self.blueprints["Storage"], self.storage_pos, progress=0)
        storage.progress = storage.blueprint.cost
        storage.passable = True
        self.buildings.append(storage)

        self.renderer = Renderer()
        self.camera = Camera()
        # Start fully zoomed out and centred on the town hall
        self.camera.set_zoom_level(len(ZOOM_LEVELS) - 1)

        # Create a single villager at the Town Hall as a demo
        self.entities.append(Villager(id=1, position=self.townhall_pos))
        self.camera.center_on(
            self.townhall_pos[0], self.townhall_pos[1], self.map.width, self.map.height
        )

        self.running = False
        # Use a higher tick rate so keyboard input is responsive
        self.tick_rate = TICK_RATE
        self.tick_count = 0
        self.paused = False
        self.single_step = False
        self.show_help = False
        self.show_actions = False
        self.show_fps = False
        self.current_fps = 0.0
        self.last_tick_ms = 0.0

        # Track overlay state so the renderer can clear when toggled.
        self._prev_show_help = False
        self._prev_show_actions = False

    # --- Resource Helpers ---------------------------------------------
    def adjust_storage(self, resource: str, amount: int) -> None:
        """Add or remove resources from global storage."""
        current_total = sum(self.storage.values())
        if amount > 0:
            available = self.storage_capacity - current_total
            if available <= 0:
                return
            amount = min(amount, available)
            self.storage[resource] = self.storage.get(resource, 0) + amount
        else:
            self.storage[resource] = self.storage.get(resource, 0) + amount
        if self.storage[resource] < 0:
            self.storage[resource] = 0

    # --- Population Helpers -----------------------------------------
    def schedule_spawn(self, position: Tuple[int, int], delay: int = 10) -> None:
        """Schedule a villager to spawn after ``delay`` ticks."""
        self.pending_spawns.append([delay, position])

    def _process_spawns(self) -> None:
        for spawn in list(self.pending_spawns):
            spawn[0] -= 1
            if spawn[0] <= 0:
                self._spawn_villager(spawn[1])
                self.pending_spawns.remove(spawn)

    def _spawn_villager(self, position: Tuple[int, int]) -> None:
        villager = Villager(id=self.next_entity_id, position=position)
        self.next_entity_id += 1
        self.entities.append(villager)

    def _find_start_pos(self) -> Tuple[int, int]:
        """Find the nearest passable tile to start the village on."""
        origin = (self.map.width // 2, self.map.height // 2)
        from collections import deque

        q = deque([origin])
        visited = {origin}
        while q:
            x, y = q.popleft()
            if self.map.get_tile(x, y).passable:
                return (x, y)
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = x + dx, y + dy
                if (
                    0 <= nx < self.map.width
                    and 0 <= ny < self.map.height
                    and (nx, ny) not in visited
                ):
                    visited.add((nx, ny))
                    q.append((nx, ny))
        return origin

    def _find_nearest_passable(self, origin: Tuple[int, int]) -> Tuple[int, int]:
        """Return the closest passable tile to ``origin``."""
        from collections import deque

        q = deque([origin])
        visited = {origin}
        while q:
            x, y = q.popleft()
            if self.map.get_tile(x, y).passable:
                return (x, y)
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = x + dx, y + dy
                if (
                    0 <= nx < self.map.width
                    and 0 <= ny < self.map.height
                    and (nx, ny) not in visited
                ):
                    visited.add((nx, ny))
                    q.append((nx, ny))
        return origin

    # --- Building Helpers --------------------------------------------
    def is_area_free(
        self, origin: Tuple[int, int], blueprint: BuildingBlueprint
    ) -> bool:
        for dx, dy in blueprint.footprint:
            x = origin[0] + dx
            y = origin[1] + dy
            if not (0 <= x < self.map.width and 0 <= y < self.map.height):
                return False
            if not self.map.get_tile(x, y).passable:
                return False
            for b in self.buildings:
                for cx, cy in getattr(
                    b, "cells", lambda: [(b.position[0], b.position[1])]
                )():
                    if cx == x and cy == y:
                        return False
        return True

    def find_build_site(
        self, blueprint: BuildingBlueprint
    ) -> Optional[Tuple[int, int]]:
        from collections import deque

        starts = [b.position for b in self.buildings] or [self.storage_pos]
        visited = set(starts)
        q = deque(starts)
        while q:
            p = q.popleft()
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                cand = (p[0] + dx, p[1] + dy)
                if cand in visited:
                    continue
                visited.add(cand)
                if self.is_area_free(cand, blueprint):
                    return cand
                q.append(cand)
        return None

    def dispatch_job(self) -> Optional[Job]:
        if self.jobs:
            return self.jobs.pop(0)

        if self.storage["wood"] < self.wood_threshold:
            return Job("gather", TileType.TREE)

        return None

    # --- Game Loop -----------------------------------------------------
    def run(self, show_fps: bool = False) -> None:
        """Run the main loop until quit."""
        self.running = True
        self.show_fps = show_fps
        term = self.renderer.term
        if self.renderer.use_curses:
            import curses

            curses.cbreak()
            curses.noecho()
            term.nodelay(True)
            try:
                last = time.perf_counter()
                while self.running:
                    start = time.perf_counter()
                    self.update()
                    self.render()
                    self.last_tick_ms = (time.perf_counter() - start) * 1000
                    self.current_fps = 1 / max(1e-6, time.perf_counter() - last)
                    last = time.perf_counter()
                    sleep = max(0, (1 / self.tick_rate) - (time.perf_counter() - start))
                    time.sleep(sleep)
            finally:
                term.nodelay(False)
                curses.nocbreak()
                curses.echo()
                curses.endwin()
        else:
            with term.cbreak(), term.hidden_cursor():
                last = time.perf_counter()
                while self.running:
                    start = time.perf_counter()
                    self.update()
                    self.render()
                    self.last_tick_ms = (time.perf_counter() - start) * 1000
                    self.current_fps = 1 / max(1e-6, time.perf_counter() - last)
                    last = time.perf_counter()
                    sleep = max(0, (1 / self.tick_rate) - (time.perf_counter() - start))
                    time.sleep(sleep)

    def update(self) -> None:
        """Process input and update world state."""
        term = self.renderer.term
        if self.renderer.use_curses:
            import curses

            ch = term.getch()
            key = ch if ch != -1 else None
        else:
            key = term.inkey(timeout=0)

        if key:
            if self.renderer.use_curses:
                if key == curses.KEY_LEFT:
                    self.camera.move(-1, 0, self.map.width, self.map.height)
                elif key == curses.KEY_RIGHT:
                    self.camera.move(1, 0, self.map.width, self.map.height)
                elif key == curses.KEY_UP:
                    self.camera.move(0, -1, self.map.width, self.map.height)
                elif key == curses.KEY_DOWN:
                    self.camera.move(0, 1, self.map.width, self.map.height)
                elif key == ord("+"):
                    self.camera.zoom_in()
                    self.camera.move(0, 0, self.map.width, self.map.height)
                elif key == ord("-"):
                    self.camera.zoom_out()
                    self.camera.move(0, 0, self.map.width, self.map.height)
                elif ord("1") <= key <= ord("9"):
                    self.camera.set_zoom_level(key - ord("1"))
                    self.camera.move(0, 0, self.map.width, self.map.height)
                elif key == ord(" "):
                    self.paused = not self.paused
                elif key == ord("."):
                    self.single_step = True
                elif key in (ord("h"), ord("H")):
                    self.show_help = not self.show_help
                elif key in (ord("a"), ord("A")):
                    self.show_actions = not self.show_actions
                elif key in (ord("c"), ord("C")):
                    self.camera.center(self.map.width, self.map.height)
                elif key in (ord("q"), ord("Q")):
                    self.running = False
            else:
                if key.code == term.KEY_LEFT:
                    self.camera.move(-1, 0, self.map.width, self.map.height)
                elif key.code == term.KEY_RIGHT:
                    self.camera.move(1, 0, self.map.width, self.map.height)
                elif key.code == term.KEY_UP:
                    self.camera.move(0, -1, self.map.width, self.map.height)
                elif key.code == term.KEY_DOWN:
                    self.camera.move(0, 1, self.map.width, self.map.height)
                elif key == "+":
                    self.camera.zoom_in()
                    self.camera.move(0, 0, self.map.width, self.map.height)
                elif key == "-":
                    self.camera.zoom_out()
                    self.camera.move(0, 0, self.map.width, self.map.height)
                elif key in "123456789":
                    self.camera.set_zoom_level(int(key) - 1)
                    self.camera.move(0, 0, self.map.width, self.map.height)
                elif key == " ":
                    self.paused = not self.paused
                elif key == ".":
                    self.single_step = True
                elif key.lower() == "h":
                    self.show_help = not self.show_help
                elif key.lower() == "a":
                    self.show_actions = not self.show_actions
                elif key.lower() == "c":
                    self.camera.center(self.map.width, self.map.height)
                elif key.lower() == "q":
                    self.running = False

        if not self.paused or self.single_step:
            for vill in self.entities:
                vill.update(self)
            self.tick_count += 1
            self.single_step = False

        # Process pending villager spawns
        self._process_spawns()

        # Auto-enqueue Lumberyards when resources allow and none are pending
        lumber_bp = self.blueprints["Lumberyard"]
        if self.storage["wood"] >= lumber_bp.cost and not any(
            b.blueprint.name == "Lumberyard" for b in self.build_queue
        ):
            pos = self.find_build_site(lumber_bp)
            if pos:
                self.storage["wood"] -= lumber_bp.cost
                building = Building(lumber_bp, pos)
                self.build_queue.append(building)
                self.buildings.append(building)
                self.jobs.append(Job("build", building))

        # House expansion and population growth
        house_bp = self.blueprints["House"]
        houses = len([b for b in self.buildings if b.blueprint.name == "House"])
        if (
            self.storage["wood"] >= house_bp.cost
            and self.storage["wood"] > self.house_threshold
            and len(self.entities) >= houses * 2
        ):
            pos = self.find_build_site(house_bp)
            if pos:
                self.storage["wood"] -= house_bp.cost
                building = Building(house_bp, pos)
                self.build_queue.append(building)
                self.buildings.append(building)
                self.jobs.append(Job("build", building))

    def render(self) -> None:
        """Draw the current game state."""
        detailed = self.camera.zoom_index >= 1

        if (
            self.show_help != self._prev_show_help
            or self.show_actions != self._prev_show_actions
        ):
            # Clear screen when overlay visibility toggles so leftover text
            # doesn't remain. Reset renderer diff tracking.
            self.renderer.clear()
            self.renderer._last_glyphs = None
            self._prev_show_help = self.show_help
            self._prev_show_actions = self.show_actions
        self.renderer.render_game(
            self.map, self.camera, self.entities, self.buildings, detailed=detailed
        )
        status = (
            f"Tick:{self.tick_count} "
            f"Cam:{self.camera.x},{self.camera.y} "
            f"Zoom:{self.camera.zoom} "
            f"Wood:{self.storage['wood']}/{self.storage_capacity} "
            f"Pop:{len(self.entities)}"
        )
        if self.show_fps:
            status += f" FPS:{self.current_fps:.1f} ({self.last_tick_ms:.1f}ms)"
        self.renderer.render_status(status)
        if self.show_help:
            lines = [
                "Controls:",
                "arrow keys - move camera",
                "+/- - zoom",
                "space - pause",
                ". - step",
                "c - centre",
                "h - toggle help",
                "q - quit",
                "1-9 - set zoom",
                "a - toggle actions",
            ]
            self.renderer.render_help(lines)

        if self.show_actions:
            start = 0
            if self.show_help:
                start = len(lines)
            lines = [f"Villager {v.id}: {v.state}" for v in self.entities]
            self.renderer.render_overlay(lines, start_y=start)
