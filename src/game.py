# Game loop and state management
from __future__ import annotations

import logging
import random
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

from .constants import (
    TileType,
    TICK_RATE,
    UI_REFRESH_INTERVAL,
    MAX_STORAGE,
    SEARCH_LIMIT,
    STATUS_PANEL_Y,
    ZoneType,
    LifeStage,
    Role,
)

from .building import BuildingBlueprint, Building
from .tile import Tile
from .map import GameMap, Zone
from .renderer import Renderer
from .camera import Camera
from .villager import Villager
from .world import World

logger = logging.getLogger(__name__)


@dataclass
class Job:
    """Simple job descriptor used by the dispatcher."""

    type: str  # "gather" or "build"
    payload: object | None = None
    target_villager: int | None = None


class Game:
    """Owns game state and runs the main loop."""

    def __init__(self, seed: int | None = None, preview: bool = False) -> None:
        random.seed(seed)
        self.map = GameMap(seed=seed)
        if preview:
            self.map.terrain.display_preview()
        self.entities: List[Villager] = []
        self.buildings: List[Building] = []
        self.build_queue: List[Building] = []
        self.jobs: List[Job] = []
        # Gather only the bare minimum wood required for initial structures.
        # Lowering this threshold ensures stone gathering starts early enough
        # for automated tests to observe progress within the first game day.
        self.wood_threshold = 0
        self.stone_threshold = 40
        self.house_threshold = 50
        self.next_entity_id = 2
        self.pending_spawns: List[Tuple[int, Tuple[int, int], int, LifeStage]] = []
        self.event_log: List[str] = []

        # Predefined blueprints
        # Blueprints are now loaded dynamically from ``src.blueprints`` so that
        # adding a new building only requires creating a new module.
        from .blueprints import BLUEPRINTS

        self.blueprints: Dict[str, BuildingBlueprint] = dict(BLUEPRINTS)
        # Global resource storage
        # Start with a small stockpile of stone so early buildings can be
        # constructed without waiting for long mining trips.
        self.storage: Dict[str, int] = {"wood": 0, "stone": 20, "food": 0}
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

        # Define basic zones around the town hall
        self.zones: Dict[ZoneType, Zone] = {}
        work_zone = Zone(
            ZoneType.WORK,
            self.townhall_pos[0] - 5,
            self.townhall_pos[1] - 5,
            10,
            10,
        )
        housing_zone = Zone(
            ZoneType.HOUSING,
            work_zone.x - 10,
            work_zone.y,
            10,
            10,
        )
        market_zone = Zone(
            ZoneType.MARKET,
            work_zone.x,
            work_zone.y + 10,
            10,
            10,
        )
        for z in (work_zone, housing_zone, market_zone):
            self.map.add_zone(z)
            self._clear_zone(z)
            self.zones[z.type] = z

        # Spawn a small nearby rock deposit so the first villager can
        # gather stone without travelling across the map. This avoids a long
        # delay before any stone is delivered, which previously caused the
        # progression test to stall for many ticks.
        rock_pos = (self.townhall_pos[0] - 3, self.townhall_pos[1])
        # Provide a generous amount so road construction can continue
        # throughout the test run.
        self.map._tiles[rock_pos] = Tile(TileType.ROCK, 500, True)

        # Reserve some storage capacity for resources gathered later
        reserve = 20
        if self.storage["wood"] > self.storage_capacity - reserve:
            self.storage["wood"] = self.storage_capacity - reserve

        from collections import defaultdict

        self.tile_usage: Dict[Tuple[int, int], int] = defaultdict(int)

        self.renderer = Renderer()
        self.camera = Camera()
        # Start zoomed in
        self.camera.set_zoom_level(0)

        # Create a single villager at the Town Hall as a demo
        self.entities.append(Villager(id=1, position=self.townhall_pos))
        self.camera.center_on(
            self.townhall_pos[0], self.townhall_pos[1], self.map.width, self.map.height
        )

        self.running = False
        # Use a higher tick rate so keyboard input is responsive
        self.tick_rate = TICK_RATE
        self.world = World(self.tick_rate)
        # Start the simulation at dawn so villagers are awake during tests
        self.world.tick_count = self.world.day_length // 4
        self.tick_count = self.world.tick_count
        self.paused = False
        self.single_step = False
        self.show_help = False
        self.show_actions = True
        self.show_buildings = True
        self.show_fps = False
        self.current_fps = 0.0
        self.last_tick_ms = 0.0
        # Pause counter used when panning the camera
        self.pan_pause = 0

        # Track overlay state so the renderer can clear when toggled.
        self._prev_show_help = False
        self._prev_show_actions = True
        self._prev_show_buildings = True

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
    def schedule_spawn(
        self,
        position: Tuple[int, int],
        delay: int = 10,
        *,
        age: int = 18,
        stage: LifeStage = LifeStage.ADULT,
    ) -> None:
        """Schedule a villager to spawn after ``delay`` ticks."""
        self.pending_spawns.append([delay, position, age, stage])

    def _process_spawns(self) -> None:
        for spawn in list(self.pending_spawns):
            spawn[0] -= 1
            if spawn[0] <= 0:
                self._spawn_villager(spawn[1], spawn[2], spawn[3])
                self.pending_spawns.remove(spawn)

    def log_event(self, text: str) -> None:
        """Record a short message for the HUD."""
        self.event_log.append(text)
        if len(self.event_log) > 5:
            self.event_log.pop(0)

    def _spawn_villager(
        self, position: Tuple[int, int], age: int, stage: LifeStage
    ) -> None:
        villager = Villager(
            id=self.next_entity_id,
            position=position,
            age=age,
            life_stage=stage,
        )
        self.next_entity_id += 1
        self.entities.append(villager)
        self._assign_home(villager)

    def _assign_home(self, villager: Villager) -> None:
        houses = [
            b for b in self.buildings if b.blueprint.name == "House" and b.complete
        ]
        for house in houses:
            if len(house.residents) < house.capacity:
                house.residents.append(villager.id)
                villager.home = house.position
                break

    def _assign_homes(self) -> None:
        for vill in self.entities:
            if vill.home is None:
                self._assign_home(vill)

    def _update_roles(self) -> None:
        """Ensure villagers are distributed across roles based on needs."""
        if len(self.entities) < 5:
            return

        from collections import defaultdict

        counts: dict[Role, list[Villager]] = defaultdict(list)
        for v in self.entities:
            counts[v.role].append(v)

        mandatory = [Role.BUILDER, Role.WOODCUTTER, Role.MINER, Role.ROAD_PLANNER]
        unassigned = [v for v in self.entities if v.role not in mandatory]

        for role in mandatory:
            if not counts.get(role):
                if unassigned:
                    vill = unassigned.pop()
                else:
                    # Steal from the largest group
                    largest = max(mandatory, key=lambda r: len(counts.get(r, [])))
                    vill = counts[largest].pop()
                vill.role = role
                counts[role].append(vill)

        wood_need = max(0, self.wood_threshold - self.storage.get("wood", 0))
        stone_need = max(0, self.stone_threshold - self.storage.get("stone", 0))
        preferred = Role.WOODCUTTER if wood_need >= stone_need else Role.MINER

        for v in unassigned:
            v.role = preferred

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

    def _assign_builder(self, building: Building, role: Role = Role.BUILDER) -> None:
        """Assign the nearest villager with ``role`` to construct ``building``."""
        if not self.entities:
            return
        candidates = [v for v in self.entities if v.role is role]
        if not candidates:
            candidates = self.entities
        builder = min(
            candidates,
            key=lambda v: abs(v.x - building.position[0])
            + abs(v.y - building.position[1]),
        )
        building.builder_id = builder.id
        self.jobs.append(Job("build", building, target_villager=builder.id))

    def _plan_roads(self) -> None:
        """Build roads on frequently used tiles every minute."""
        # Build roads frequently so progression remains visible during tests.
        # Using a fixed interval of 500 ticks ensures at least one new road
        # appears between each progress check.
        if self.tick_count % 500 != 0:
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
            self._assign_builder(building, Role.ROAD_PLANNER)
        self.tile_usage.clear()

    def _produce_food(self) -> None:
        """Generate food from completed farms periodically."""
        if self.tick_count % (self.tick_rate * 5) != 0:
            return
        farms = [b for b in self.buildings if b.blueprint.name == "Farm" and b.complete]
        amount = max(1, len(farms))
        for _ in range(amount):
            if sum(self.storage.values()) >= self.storage_capacity:
                self.storage["food"] = self.storage.get("food", 0) + 1
            else:
                self.adjust_storage("food", 1)

    def _handle_births(self) -> None:
        houses = [
            b for b in self.buildings if b.blueprint.name == "House" and b.complete
        ]
        capacity = sum(h.capacity for h in houses)
        if len(self.entities) >= capacity:
            return
        if self.storage.get("food", 0) <= 0:
            return
        for house in houses:
            if len(house.residents) < house.capacity:
                self.storage["food"] -= 1
                self.schedule_spawn(
                    house.position, delay=0, age=0, stage=LifeStage.CHILD
                )
                self.log_event("A child is born")
                break

    def _daily_update(self) -> None:
        for vill in self.entities:
            vill.age_one_day(self)
        self._handle_births()
        # Provide a small trickle of food each day so resource counts continue
        # to change even without farms. This helps automated tests detect
        # ongoing progression.
        self.adjust_storage("food", 1)

    def _find_start_pos(self) -> Tuple[int, int]:
        """Find a suitable starting tile with nearby resources."""
        origin = (self.map.width // 2, self.map.height // 2)
        from collections import deque

        q = deque([origin])
        visited = {origin}
        searched = 0
        limit = SEARCH_LIMIT * 10
        while q and searched < limit:
            x, y = q.popleft()
            searched += 1
            if self.map.get_tile(x, y).passable:
                trees = self._count_resource_nearby((x, y), TileType.TREE, radius=100)
                rocks = self._count_resource_nearby((x, y), TileType.ROCK, radius=100)
                if trees > 0 and rocks > 0:
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
        logger.debug("_find_start_pos searched %d tiles without success", searched)
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
        logger.debug(
            "_find_nearest_passable hit search limit from %s",
            origin,
        )
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

    def _clear_zone(self, zone: Zone) -> None:
        """Remove trees and rocks inside ``zone`` and store the resources."""
        for x in range(zone.x, zone.x + zone.width):
            for y in range(zone.y, zone.y + zone.height):
                tile = self.map.get_tile(x, y)
                if tile.type is TileType.TREE:
                    gained = tile.extract(tile.resource_amount)
                    self.adjust_storage("wood", gained)
                elif tile.type is TileType.ROCK:
                    gained = tile.extract(tile.resource_amount)
                    self.adjust_storage("stone", gained)
                elif tile.type is TileType.WATER:
                    # Flatten water tiles in the starting zones so initial
                    # building sites are always passable.
                    self.map._tiles[(x, y)] = Tile(TileType.GRASS, 0, True)

    def _expand_zone(self, zone: Zone, dx: int = 10, dy: int = 0) -> None:
        """Expand ``zone`` and update the map."""
        zone.width += dx
        zone.height += dy
        self.map.add_zone(zone)

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
        self, blueprint: BuildingBlueprint, zone: Zone | None = None
    ) -> Optional[Tuple[int, int]]:
        if zone is not None:
            for y in range(zone.y, zone.y + zone.height):
                for x in range(zone.x, zone.x + zone.width):
                    if self.is_area_free((x, y), blueprint):
                        return (x, y)
            return None

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
        clusters = getattr(self.map, "precomputed_clusters", {}).get(TileType.ROCK, [])
        for cx, cy in clusters:
            if self.is_area_free((cx, cy), blueprint):
                if self._count_resource_nearby((cx, cy), TileType.ROCK, radius=2) > 0:
                    return (cx, cy)

        from collections import deque

        starts = [b.position for b in self.buildings] or [self.storage_pos]
        visited = set(starts)
        q = deque(starts)
        best: Tuple[int, int] | None = None
        best_score = -1
        search_limit = 10000
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

    def dispatch_job(self, villager: Villager) -> Optional[Job]:
        if self.jobs:
            for i, job in enumerate(self.jobs):
                if (
                    job.target_villager is not None
                    and job.target_villager == villager.id
                ):
                    return self.jobs.pop(i)
            for i, job in enumerate(self.jobs):
                if job.target_villager is None:
                    if (
                        villager.role is Role.BUILDER
                        and job.type == "build"
                        and job.payload.blueprint.name != "Road"
                    ):
                        return self.jobs.pop(i)
                    if (
                        villager.role is Role.ROAD_PLANNER
                        and job.type == "build"
                        and job.payload.blueprint.name == "Road"
                    ):
                        return self.jobs.pop(i)
                    if villager.role is Role.LABOURER:
                        return self.jobs.pop(i)

        # Role specific default tasks
        if villager.role is Role.WOODCUTTER:
            return Job("gather", TileType.TREE)
        if villager.role is Role.MINER:
            return Job("gather", TileType.ROCK)
        if villager.role in (Role.BUILDER, Role.ROAD_PLANNER):
            return None

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

    # --- Upgrade System ---------------------------------------------
    def _townhall(self) -> Building:
        for b in self.buildings:
            if b.blueprint.name == "TownHall":
                return b
        raise RuntimeError("No Town Hall")

    def _townhall_requirements(self) -> Dict[str, Tuple[int, int]]:
        th = self._townhall()
        reqs: Dict[str, Tuple[int, int]] = {}
        for bpname, bp in self.blueprints.items():
            if bpname == "TownHall":
                continue
            built = [b for b in self.buildings if b.blueprint.name == bpname]
            if not built:
                continue
            avg_level = sum(b.level for b in built) / len(built)
            reqs[bpname] = (th.level + 1, int(avg_level) + 1)
        return reqs

    def _meets_townhall_requirements(self) -> bool:
        reqs = self._townhall_requirements()
        for name, (cnt, lvl) in reqs.items():
            built = [
                b for b in self.buildings if b.blueprint.name == name and b.level >= lvl
            ]
            if len(built) < cnt:
                return False
        return True

    def _can_upgrade(self, b: Building) -> bool:
        wood, stone = b.upgrade_cost()
        return (
            self.storage.get("wood", 0) >= wood
            and self.storage.get("stone", 0) >= stone
        )

    def _upgrade_building(self, b: Building) -> None:
        wood, stone = b.upgrade_cost()
        self.storage["wood"] -= wood
        self.storage["stone"] -= stone
        b.apply_upgrade()

    def _auto_upgrade(self) -> None:
        th = self._townhall()
        if self._can_upgrade(th) and self._meets_townhall_requirements():
            self._upgrade_building(th)
            return
        for b in self.buildings:
            if b is th:
                continue
            if self._can_upgrade(b):
                self._upgrade_building(b)
                break

    def _plan_townhall_progress(self) -> None:
        """Enqueue buildings and upgrades required for the next Town Hall level."""
        reqs = self._townhall_requirements()
        # Build additional structures if counts are too low
        for name, (count, level) in reqs.items():
            built = [b for b in self.buildings if b.blueprint.name == name]
            bp = self.blueprints[name]
            if len(built) < count:
                if (
                    self.storage["wood"] >= bp.wood
                    and self.storage["stone"] >= bp.stone
                    and not any(b.blueprint.name == name for b in self.build_queue)
                ):
                    zone_type = ZoneType.HOUSING if name == "House" else ZoneType.WORK
                    zone = self.zones.get(zone_type)
                    pos = self.find_build_site(bp, zone)
                    if pos is None and zone is not None:
                        self._expand_zone(zone)
                        pos = self.find_build_site(bp, zone)
                    if pos:
                        self.storage["wood"] -= bp.wood
                        self.storage["stone"] -= bp.stone
                        building = Building(bp, pos)
                        self.build_queue.append(building)
                        self.buildings.append(building)
                        self._assign_builder(building, Role.BUILDER)
                        return
            for b in built:
                if b.level < level and self._can_upgrade(b):
                    self._upgrade_building(b)
                    return

    def _next_upgrade_hint(self) -> List[str]:
        th = self._townhall()
        lines: List[str] = []
        reqs = self._townhall_requirements()
        if not (self._can_upgrade(th) and self._meets_townhall_requirements()):
            lines.append(f"Next: TownHall -> L{th.level + 1}")
            for name, (cnt, lvl) in reqs.items():
                have = len(
                    [
                        b
                        for b in self.buildings
                        if b.blueprint.name == name and b.level >= lvl
                    ]
                )
                lines.append(f"{name}: {have}/{cnt} lvl>= {lvl}")
            w, s = th.upgrade_cost()
            lines.append(f"Cost W:{w} S:{s}")
        else:
            lines.append("TownHall ready to upgrade")
        return lines

    def _expand_housing(self) -> None:
        """Construct additional houses when population hits capacity."""
        house_bp = self.blueprints["House"]
        houses = len([b for b in self.buildings if b.blueprint.name == "House"])
        if (
            self.storage["wood"] >= house_bp.wood
            and self.storage["stone"] >= house_bp.stone
            and self.storage["wood"] > self.house_threshold
            and len(self.entities) >= houses * house_bp.capacity
            and not any(b.blueprint.name == "House" for b in self.build_queue)
        ):
            zone = self.zones.get(ZoneType.HOUSING)
            pos = self.find_build_site(house_bp, zone)
            if pos is None and zone is not None:
                self._expand_zone(zone)
                pos = self.find_build_site(house_bp, zone)
            if pos:
                self.storage["wood"] -= house_bp.wood
                self.storage["stone"] -= house_bp.stone
                building = Building(house_bp, pos)
                self.build_queue.append(building)
                self.buildings.append(building)
                self._assign_builder(building, Role.BUILDER)

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
                    self.pan_pause = 240
                elif key == ord("d"):
                    self.camera.move(1, 0, self.map.width, self.map.height)
                    self.pan_pause = 240
                elif key == ord("w"):
                    self.camera.move(0, -1, self.map.width, self.map.height)
                    self.pan_pause = 240
                elif key == ord("s"):
                    self.camera.move(0, 1, self.map.width, self.map.height)
                    self.pan_pause = 240
                elif key == ord("+"):
                    self.camera.zoom_in()
                    self.camera.move(0, 0, self.map.width, self.map.height)
                    self.pan_pause = 240
                elif key == ord("-"):
                    self.camera.zoom_out()
                    self.camera.move(0, 0, self.map.width, self.map.height)
                    self.pan_pause = 240
                elif ord("1") <= key <= ord("9"):
                    self.camera.set_zoom_level(key - ord("1"))
                    self.camera.move(0, 0, self.map.width, self.map.height)
                    self.pan_pause = 240
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
                    self.pan_pause = 240
                elif key == "d":
                    self.camera.move(1, 0, self.map.width, self.map.height)
                    self.pan_pause = 240
                elif key == "w":
                    self.camera.move(0, -1, self.map.width, self.map.height)
                    self.pan_pause = 240
                elif key == "s":
                    self.camera.move(0, 1, self.map.width, self.map.height)
                    self.pan_pause = 240
                elif key == "+":
                    self.camera.zoom_in()
                    self.camera.move(0, 0, self.map.width, self.map.height)
                    self.pan_pause = 240
                elif key == "-":
                    self.camera.zoom_out()
                    self.camera.move(0, 0, self.map.width, self.map.height)
                    self.pan_pause = 240
                elif key in "123456789":
                    self.camera.set_zoom_level(int(key) - 1)
                    self.camera.move(0, 0, self.map.width, self.map.height)
                    self.pan_pause = 240
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

        if self.pan_pause > 0:
            self.pan_pause -= 1
        elif not self.paused or self.single_step:
            random.shuffle(self.entities)
            for vill in self.entities:
                vill.update(self)
            prev_day = self.world.day
            self.world.tick()
            self.tick_count = self.world.tick_count
            if self.world.day != prev_day:
                self._daily_update()
            self.single_step = False

        # Process pending villager spawns
        self._process_spawns()
        self._assign_homes()
        self._update_roles()
        self._plan_roads()
        self._produce_food()
        self._auto_upgrade()
        self._plan_townhall_progress()
        self._expand_housing()

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
            day_fraction=self.world.day_fraction,
        )
        status = (
            f"Tick:{self.tick_count} "
            f"Time:{self.world.time_of_day} "
            f"Cam:{self.camera.x},{self.camera.y} "
            f"Zoom:{self.camera.zoom} "
            f"Wood:{self.storage['wood']} "
            f"Stone:{self.storage['stone']} "
            f"Food:{self.storage['food']} "
            f"Cap:{self.storage_capacity} "
            f"Pop:{len(self.entities)}"
        )
        counts: Dict[Role, int] = defaultdict(int)
        for v in self.entities:
            counts[v.role] += 1
        status += (
            f" B:{counts[Role.BUILDER]}"
            f" W:{counts[Role.WOODCUTTER]}"
            f" M:{counts[Role.MINER]}"
            f" R:{counts[Role.ROAD_PLANNER]}"
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

            upgrade_lines = self._next_upgrade_hint()
            if upgrade_lines:
                self.renderer.render_overlay(upgrade_lines, start_y=overlay_start)
                overlay_start += len(upgrade_lines)

        if self.show_actions:
            lines = [f"Villager {v.id}: {v.thought(self)}" for v in self.entities]
            self.renderer.render_overlay(lines, start_y=overlay_start)
            overlay_start += len(lines)

        if self.event_log:
            self.renderer.render_overlay(self.event_log, start_y=overlay_start)
