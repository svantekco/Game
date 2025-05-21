# Game loop and state management
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

from .constants import (
    TileType,
    ZOOM_LEVELS,
    TICK_RATE,
    UI_REFRESH_INTERVAL,
    MAX_STORAGE,
    SEARCH_LIMIT,
    STATUS_PANEL_Y,
)

from .building import BuildingBlueprint, Building

from .map import GameMap
from .renderer import Renderer
from .world import World

from .camera import Camera
from .villager import Villager


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
        self.stone_threshold = 40
        self.house_threshold = 50
        self.next_entity_id = 2
        self.pending_spawns: List[Tuple[int, Tuple[int, int]]] = []

        # Predefined blueprints
        # Blueprints are now loaded dynamically from ``src.blueprints`` so that
        # adding a new building only requires creating a new module.
        from .blueprints import BLUEPRINTS

        self.blueprints: Dict[str, BuildingBlueprint] = dict(BLUEPRINTS)
        # Global resource storage
        self.storage: Dict[str, int] = {"wood": 0, "stone": 0, "food": 0}
        self.storage_capacity = MAX_STORAGE

        # Place Town Hall at the starting location
        self.townhall_pos: Tuple[int, int] = self._find_start_pos()
        townhall = Building(self.blueprints["TownHall"], self.townhall_pos, progress=0)
        townhall.progress = townhall.blueprint.build_time
        townhall.passable = True
        self.buildings.append(townhall)

        # Place initial Storage building 5 tiles east of the Town Hall
        candidate = (self.townhall_pos[0] + 5, self.townhall_pos[1])
        self.storage_pos = self._find_nearest_passable(candidate)
        storage = Building(self.blueprints["Storage"], self.storage_pos, progress=0)
        storage.progress = storage.blueprint.build_time
        storage.passable = True
        self.buildings.append(storage)
        self.storage_positions: List[Tuple[int, int]] = [self.storage_pos]

        from collections import defaultdict

        self.tile_usage: Dict[Tuple[int, int], int] = defaultdict(int)

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
        self.world = World(self.tick_rate)
        self.paused = False
        self.single_step = False
        self.show_help = False
        self.show_actions = False
        self.show_buildings = False
        self.show_fps = False
        self.current_fps = 0.0
        self.last_tick_ms = 0.0

        # Track overlay state so the renderer can clear when toggled.
        self._prev_show_help = False
        self._prev_show_actions = False
        self._prev_show_buildings = False

        # Next tick count when a full UI refresh should occur
        self._next_ui_refresh = UI_REFRESH_INTERVAL

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
        self._assign_home(villager)

    def _assign_home(self, villager: Villager) -> None:
        houses = [
            b for b in self.buildings if b.blueprint.name == "House" and b.complete
        ]
        for house in houses:
            if len(house.residents) < 2:
                house.residents.append(villager.id)
                villager.home = house.position
                break

    def _assign_homes(self) -> None:
        for vill in self.entities:
            if vill.home is None:
                self._assign_home(vill)

    # --- Usage Tracking ---------------------------------------------
    def record_tile_usage(self, pos: Tuple[int, int]) -> None:
        """Increment usage counter for ``pos``."""
        self.tile_usage[pos] += 1

    def nearest_storage(self, pos: Tuple[int, int]) -> Tuple[int, int]:
        """Return the closest storage location to ``pos``."""
        return min(
            self.storage_positions,
            key=lambda s: abs(s[0] - pos[0]) + abs(s[1] - pos[1]),
        )

    def _plan_roads(self) -> None:
        """Build roads on frequently used tiles every minute."""
        if self.tick_count % (self.tick_rate * 60) != 0:
            return
        road_bp = self.blueprints["Road"]
        if self.storage["stone"] < road_bp.stone:
            return
        # Select top 5 most used tiles
        candidates = sorted(
            self.tile_usage.items(), key=lambda kv: kv[1], reverse=True
        )[:5]
        for (x, y), _ in candidates:
            if self.storage["stone"] < road_bp.stone:
                break
            tile = self.map.get_tile(x, y)
            if not tile.passable:
                continue
            if any(b.position == (x, y) for b in self.buildings):
                continue
            building = Building(road_bp, (x, y))
            self.storage["stone"] -= road_bp.stone
            self.build_queue.append(building)
            self.buildings.append(building)
            self.jobs.append(Job("build", building))
        self.tile_usage.clear()

    def _produce_food(self) -> None:
        """Generate food from completed farms periodically."""
        if self.tick_count % (self.tick_rate * 5) != 0:
            return
        farms = [b for b in self.buildings if b.blueprint.name == "Farm" and b.complete]
        for _ in farms:
            self.adjust_storage("food", 1)

    def _find_start_pos(self) -> Tuple[int, int]:
        """Find the nearest passable tile to start the village on."""
        origin = (self.map.width // 2, self.map.height // 2)
        from collections import deque

        q = deque([origin])
        visited = {origin}
        searched = 0
        while q and searched < SEARCH_LIMIT:
            x, y = q.popleft()
            searched += 1
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
        searched = 0
        while q and searched < SEARCH_LIMIT:
            x, y = q.popleft()
            searched += 1
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

    def _count_resource_nearby(
        self, origin: Tuple[int, int], resource: TileType, radius: int
    ) -> int:
        """Count resource tiles of type ``resource`` within ``radius``."""
        count = 0
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                x, y = origin[0] + dx, origin[1] + dy
                if not (0 <= x < self.map.width and 0 <= y < self.map.height):
                    continue
                tile = self.map.get_tile(x, y)
                if tile.type is resource and tile.resource_amount > 0:
                    count += 1
        return count

    def get_search_limit(self) -> int:
        """Return BFS search limit factoring in built Watchtowers."""
        bonus = sum(
            1 for b in self.buildings if b.blueprint.name == "Watchtower" and b.complete
        )
        return SEARCH_LIMIT + bonus * 5000

    # --- Building Helpers --------------------------------------------
    def is_area_free(
        self, origin: Tuple[int, int], blueprint: BuildingBlueprint
    ) -> bool:
        cells = [(origin[0] + dx, origin[1] + dy) for dx, dy in blueprint.footprint]
        for x, y in cells:
            if not (0 <= x < self.map.width and 0 <= y < self.map.height):
                return False
            if not self.map.get_tile(x, y).passable:
                return False
        for b in self.buildings:
            for cx, cy in getattr(
                b, "cells", lambda: [(b.position[0], b.position[1])]
            )():
                for x, y in cells:
                    if abs(cx - x) <= 2 and abs(cy - y) <= 2:
                        return False
        return True

    def find_build_site(
        self, blueprint: BuildingBlueprint
    ) -> Optional[Tuple[int, int]]:
        from collections import deque

        starts = [b.position for b in self.buildings] or [self.storage_pos]
        visited = set(starts)
        q = deque(starts)
        searched = 0
        while q and searched < SEARCH_LIMIT:
            p = q.popleft()
            searched += 1
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                cand = (p[0] + dx, p[1] + dy)
                if cand in visited:
                    continue
                visited.add(cand)
                if self.is_area_free(cand, blueprint):
                    return cand
                q.append(cand)
        return None

    def find_quarry_site(
        self, blueprint: BuildingBlueprint
    ) -> Optional[Tuple[int, int]]:
        """Find a quarry site near existing buildings prioritising stone density."""
        from collections import deque

        starts = [b.position for b in self.buildings] or [self.storage_pos]
        visited = set(starts)
        q = deque(starts)
        best: Tuple[int, int] | None = None
        best_score = -1
        search_limit = 500
        searched = 0
        while q and searched < search_limit:
            p = q.popleft()
            searched += 1
            if self.is_area_free(p, blueprint):
                score = self._count_resource_nearby(p, TileType.ROCK, radius=5)
                if score > best_score:
                    best = p
                    best_score = score
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                cand = (p[0] + dx, p[1] + dy)
                if cand in visited:
                    continue
                visited.add(cand)
                q.append(cand)
        return best if best_score > 0 else None

    def dispatch_job(self) -> Optional[Job]:
        if self.jobs:
            return self.jobs.pop(0)

        # Ensure we always have enough resources to build new storage
        storage_bp = self.blueprints["Storage"]
        if self.storage["wood"] < storage_bp.wood:
            return Job("gather", TileType.TREE)
        if self.storage["stone"] < storage_bp.stone:
            return Job("gather", TileType.ROCK)

        if self.storage["wood"] < self.wood_threshold:
            return Job("gather", TileType.TREE)

        if self.storage["stone"] < self.stone_threshold:
            return Job("gather", TileType.ROCK)

        # Default to gathering wood so villagers never stay idle
        return Job("gather", TileType.TREE)

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
            ch = term.getch()
            key = ch if ch != -1 else None
        else:
            key = term.inkey(timeout=0)

        if key:
            if self.renderer.use_curses:
                if key == ord("a"):
                    self.camera.move(-1, 0, self.map.width, self.map.height)
                elif key == ord("d"):
                    self.camera.move(1, 0, self.map.width, self.map.height)
                elif key == ord("w"):
                    self.camera.move(0, -1, self.map.width, self.map.height)
                elif key == ord("s"):
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
                elif key == ord("A"):
                    self.show_actions = not self.show_actions
                elif key in (ord("B"), ord("b")):
                    self.show_buildings = not self.show_buildings
                elif key in (ord("c"), ord("C")):
                    self.camera.center(self.map.width, self.map.height)
                elif key in (ord("q"), ord("Q")):
                    self.running = False
            else:
                if key == "a":
                    self.camera.move(-1, 0, self.map.width, self.map.height)
                elif key == "d":
                    self.camera.move(1, 0, self.map.width, self.map.height)
                elif key == "w":
                    self.camera.move(0, -1, self.map.width, self.map.height)
                elif key == "s":
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
                elif key == "A":
                    self.show_actions = not self.show_actions
                elif key.lower() == "b":
                    self.show_buildings = not self.show_buildings
                elif key.lower() == "c":
                    self.camera.center(self.map.width, self.map.height)
                elif key.lower() == "q":
                    self.running = False

        if not self.paused or self.single_step:
            for vill in self.entities:
                vill.update(self)
            self.world.tick()
            self.tick_count = self.world.tick_count
            self.single_step = False

        # Process pending villager spawns
        self._process_spawns()
        self._assign_homes()
        self._plan_roads()
        self._produce_food()

        # Prioritise building a Quarry when possible
        quarry_bp = self.blueprints["Quarry"]
        if (
            self.storage["wood"] >= quarry_bp.wood
            and self.storage["stone"] >= quarry_bp.stone
            and not any(b.blueprint.name == "Quarry" for b in self.build_queue)
            and not any(b.blueprint.name == "Quarry" for b in self.buildings)
        ):
            pos = self.find_quarry_site(quarry_bp)
            if pos:
                self.storage["wood"] -= quarry_bp.wood
                self.storage["stone"] -= quarry_bp.stone
                building = Building(quarry_bp, pos)
                self.build_queue.append(building)
                self.buildings.append(building)
                self.jobs.append(Job("build", building))

        # Build additional storage when nearing capacity
        storage_bp = self.blueprints["Storage"]
        total = sum(self.storage.values())
        if (
            total >= self.storage_capacity - 20
            and self.storage["wood"] >= storage_bp.wood
            and self.storage["stone"] >= storage_bp.stone
            and not any(b.blueprint.name == "Storage" for b in self.build_queue)
        ):
            pos = self.find_build_site(storage_bp)
            if pos:
                self.storage["wood"] -= storage_bp.wood
                self.storage["stone"] -= storage_bp.stone
                building = Building(storage_bp, pos, progress=0)
                building.progress = storage_bp.build_time
                building.passable = True
                self.buildings.append(building)
                self.storage_capacity += MAX_STORAGE
                self.storage_pos = pos
                self.storage_positions.append(pos)

        # Auto-enqueue Lumberyards when resources allow and none are pending
        lumber_bp = self.blueprints["Lumberyard"]
        if (
            self.storage["wood"] >= lumber_bp.wood
            and self.storage["stone"] >= lumber_bp.stone
            and not any(b.blueprint.name == "Lumberyard" for b in self.build_queue)
            and not any(b.blueprint.name == "Lumberyard" for b in self.buildings)
        ):
            pos = self.find_build_site(lumber_bp)
            if pos:
                self.storage["wood"] -= lumber_bp.wood
                self.storage["stone"] -= lumber_bp.stone
                building = Building(lumber_bp, pos)
                self.build_queue.append(building)
                self.buildings.append(building)
                self.jobs.append(Job("build", building))

        # Build a Blacksmith when resources allow and none exist
        black_bp = self.blueprints.get("Blacksmith")
        if black_bp and (
            self.storage["wood"] >= black_bp.wood
            and self.storage["stone"] >= black_bp.stone
            and not any(b.blueprint.name == "Blacksmith" for b in self.build_queue)
            and not any(b.blueprint.name == "Blacksmith" for b in self.buildings)
        ):
            pos = self.find_build_site(black_bp)
            if pos:
                self.storage["wood"] -= black_bp.wood
                self.storage["stone"] -= black_bp.stone
                building = Building(black_bp, pos)
                self.build_queue.append(building)
                self.buildings.append(building)
                self.jobs.append(Job("build", building))

        # House expansion and population growth
        house_bp = self.blueprints["House"]
        houses = len([b for b in self.buildings if b.blueprint.name == "House"])
        if (
            self.storage["wood"] >= house_bp.wood
            and self.storage["stone"] >= house_bp.stone
            and self.storage["wood"] > self.house_threshold
            and len(self.entities) >= houses * 2
        ):
            pos = self.find_build_site(house_bp)
            if pos:
                self.storage["wood"] -= house_bp.wood
                self.storage["stone"] -= house_bp.stone
                building = Building(house_bp, pos)
                self.build_queue.append(building)
                self.buildings.append(building)
                self.jobs.append(Job("build", building))

    def render(self) -> None:
        """Draw the current game state."""
        detailed = self.camera.zoom_index >= 1

        if self.tick_count >= self._next_ui_refresh:
            # Force a full redraw periodically to prevent UI artifacts
            self.renderer.clear()
            self.renderer._last_glyphs = None
            self.renderer._last_colors = None
            self._next_ui_refresh = self.tick_count + UI_REFRESH_INTERVAL

        if (
            self.show_help != self._prev_show_help
            or self.show_actions != self._prev_show_actions
            or self.show_buildings != self._prev_show_buildings
        ):
            # Clear screen when overlay visibility toggles so leftover text
            # doesn't remain. Reset renderer diff tracking.
            self.renderer.clear()
            self.renderer._last_glyphs = None
            self._prev_show_help = self.show_help
            self._prev_show_actions = self.show_actions
            self._prev_show_buildings = self.show_buildings
        self.renderer.render_game(
            self.map,
            self.camera,
            self.entities,
            self.buildings,
            detailed=detailed,
            is_night=self.world.is_night,
        )
        status = (
            f"Tick:{self.tick_count} "
            f"Cam:{self.camera.x},{self.camera.y} "
            f"Zoom:{self.camera.zoom} "
            f"Wood:{self.storage['wood']} "
            f"Stone:{self.storage['stone']} "
            f"Food:{self.storage['food']} "
            f"Cap:{self.storage_capacity} "
            f"Pop:{len(self.entities)}"
        )
        if self.show_fps:
            status += f" FPS:{self.current_fps:.1f} ({self.last_tick_ms:.1f}ms)"
        self.renderer.render_status(status)
        overlay_start = STATUS_PANEL_Y + 1
        if self.show_help:
            lines = [
                "Controls:",
                "WASD - move camera",
                "+/- - zoom",
                "space - pause",
                ". - step",
                "c - centre",
                "h - toggle help",
                "b - toggle buildings",
                "q - quit",
                "1-9 - set zoom",
                "A - toggle thoughts",
            ]
            self.renderer.render_help(lines, start_y=overlay_start)
            overlay_start += len(lines)

        if self.show_buildings:
            counts: Dict[str, int] = defaultdict(int)
            for b in self.buildings:
                counts[b.blueprint.name] += 1
            build_lines = [f"{name}: {cnt}" for name, cnt in counts.items()]
            self.renderer.render_overlay(build_lines, start_y=overlay_start)
            overlay_start += len(build_lines)

            progress_lines = []
            for b in self.build_queue:
                if b.blueprint.build_time > 0:
                    pct = int(100 * b.progress / b.blueprint.build_time)
                    progress_lines.append(f"{b.blueprint.name} {pct}%")
            if progress_lines:
                self.renderer.render_overlay(progress_lines, start_y=overlay_start)
                overlay_start += len(progress_lines)

        if self.show_actions:
            lines = [f"Villager {v.id}: {v.thought(self)}" for v in self.entities]
            self.renderer.render_overlay(lines, start_y=overlay_start)
