from __future__ import annotations

import random
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

if TYPE_CHECKING:  # pragma: no cover - imports for type hints only
    from .game import Game

from .building import Building
from .constants import (
    CARRY_CAPACITY,
    Mood,
    Personality,
    TileType,
    VILLAGER_ACTION_DELAY,
    LifeStage,
    Role,
)
from .pathfinding import (
    find_nearest_resource,
    find_path_fast,
    find_path_to_building_adjacent,
)

logger = logging.getLogger(__name__)


@dataclass
class Villager:
    """Autonomous villager entity with a simple behaviour tree."""

    id: int
    position: Tuple[int, int]
    state: str = "idle"
    inventory: Dict[str, int] = field(default_factory=lambda: {"wood": 0, "stone": 0})
    carrying_capacity: int = CARRY_CAPACITY
    target_path: List[Tuple[int, int]] = field(default_factory=list)
    target_resource: Optional[Tuple[int, int]] = None
    resource_type: Optional[TileType] = None
    target_building: Optional[Building] = None
    target_storage: Optional[Tuple[int, int]] = None
    cooldown: int = 0
    personality: Personality = field(
        default_factory=lambda: random.choice(list(Personality))
    )
    mood: Mood = Mood.NEUTRAL
    home: Optional[Tuple[int, int]] = None
    asleep: bool = False
    age: int = 18
    life_stage: LifeStage = LifeStage.ADULT
    role: Role = Role.LABOURER
    reservations: Dict[TileType, Tuple[int, int] | None] = field(default_factory=dict)

    # ---------------------------------------------------------------
    def is_full(self) -> bool:
        return sum(self.inventory.values()) >= self.carrying_capacity

    def _apply_tool_bonus(self, game: "Game", delay: int) -> int:
        for b in game.buildings:
            if b.blueprint.name == "Blacksmith" and b.complete:
                bx, by = b.position
                if abs(bx - self.position[0]) <= 5 and abs(by - self.position[1]) <= 5:
                    return max(0, delay // 2)
        return delay

    def _personality_delay_factor(self) -> float:
        if self.personality is Personality.LAZY:
            return 1.2
        if self.personality is Personality.INDUSTRIOUS:
            return 0.8
        return 1.0

    def _mood_delay_factor(self) -> float:
        if self.mood is Mood.HAPPY:
            return 0.9
        if self.mood is Mood.SAD:
            return 1.1
        return 1.0

    def _life_stage_delay_factor(self) -> float:
        if self.life_stage is LifeStage.CHILD:
            return 1.5
        if self.life_stage is LifeStage.ELDER:
            return 1.2
        if self.life_stage is LifeStage.RETIRED:
            return 2.0
        return 1.0

    def _time_of_day_delay_factor(self, game: "Game") -> float:
        """Return slowdown factor for night time."""
        return 1.5 if game.world.is_night else 1.0

    def _action_delay(self, game: "Game", base_delay: int) -> int:
        delay = self._apply_tool_bonus(game, base_delay)
        delay = int(
            delay
            * self._personality_delay_factor()
            * self._mood_delay_factor()
            * self._life_stage_delay_factor()
            * self._time_of_day_delay_factor(game)
        )

        # Introduce a small random variation so actions don't all complete at
        # exactly the same intervals.  Personalities and mood influence how
        # large the jitter can be.  Industrious/happy villagers tend to be more
        # consistent, while lazy/sad villagers vary more.
        variation = 0.1
        if self.personality is Personality.INDUSTRIOUS:
            variation *= 0.8
        elif self.personality is Personality.LAZY:
            variation *= 1.2
        if self.mood is Mood.HAPPY:
            variation *= 0.8
        elif self.mood is Mood.SAD:
            variation *= 1.2
        delay = int(delay * random.uniform(1 - variation, 1 + variation))

        return max(0, delay)

    def adjust_mood(self, delta: int) -> None:
        levels = [Mood.SAD, Mood.NEUTRAL, Mood.HAPPY]
        idx = levels.index(self.mood)
        idx = max(0, min(len(levels) - 1, idx + delta))
        self.mood = levels[idx]

    # ------------------------------------------------------------------
    def _move_away_from(self, other: Tuple[int, int], game: "Game") -> bool:
        """Step one tile away from ``other`` if possible."""

        options = []
        dx = self.position[0] - other[0]
        dy = self.position[1] - other[1]
        if dx != 0:
            step_x = self.position[0] + (1 if dx > 0 else -1)
            options.append((step_x, self.position[1]))
        if dy != 0:
            step_y = self.position[1] + (1 if dy > 0 else -1)
            options.append((self.position[0], step_y))
        random.shuffle(options)
        for nx, ny in options:
            if not (0 <= nx < game.map.width and 0 <= ny < game.map.height):
                continue
            tile = game.map.get_tile(nx, ny)
            if not tile.passable:
                continue
            if any(v.position == (nx, ny) for v in game.entities if v is not self):
                continue
            blocked = False
            for b in game.buildings:
                cells = b.cells() if hasattr(b, "cells") else [b.position]
                if (nx, ny) in cells and not b.passable:
                    blocked = True
                    break
            if blocked:
                continue
            self.target_path = [(nx, ny)]
            return self._move_step(game)
        return False

    def _avoid_nearby_villagers(self, game: "Game") -> bool:
        """Disabled: previously stepped away from nearby villagers."""
        return False

    def _move_step(self, game: "Game") -> bool:
        if not self.target_path:
            return False
        next_pos = self.target_path[0]
        # Allow passing other villagers, only block if another villager is idle on the tile
        for v in game.entities:
            if v is self:
                continue
            if v.position == next_pos:
                if v.target_path and v.target_path[0] == self.position:
                    # swap positions, other villager moves later
                    break
                return False
        tile = game.map.get_tile(*next_pos)
        if not tile.passable:
            self.target_path = []
            logger.debug(
                "Villager %s blocked by impassable tile at %s", self.id, next_pos
            )
            return False
        for b in game.buildings:
            cells = b.cells() if hasattr(b, "cells") else [b.position]
            if next_pos in cells and not b.passable:
                self.target_path = []
                logger.debug("Villager %s blocked by building at %s", self.id, next_pos)
                return False

        self.position = self.target_path.pop(0)
        game.record_tile_usage(self.position)
        tile = game.map.get_tile(*self.position)
        delay = VILLAGER_ACTION_DELAY
        if tile.type is TileType.TREE:
            delay *= 2
        elif tile.type is TileType.ROCK:
            delay *= 3
        for b in game.buildings:
            if (
                b.position == self.position
                and b.blueprint.name == "Road"
                and b.complete
            ):
                delay = max(1, delay // 2)
                break
        self.cooldown = self._action_delay(game, delay)
        return True

    def _wander(self, game: "Game") -> bool:
        """Move to a random adjacent passable tile."""
        neighbors = [
            (self.position[0] + 1, self.position[1]),
            (self.position[0] - 1, self.position[1]),
            (self.position[0], self.position[1] + 1),
            (self.position[0], self.position[1] - 1),
        ]
        random.shuffle(neighbors)
        for nx, ny in neighbors:
            if not (0 <= nx < game.map.width and 0 <= ny < game.map.height):
                continue
            tile = game.map.get_tile(nx, ny)
            if not tile.passable:
                continue
            blocked = False
            for b in game.buildings:
                cells = b.cells() if hasattr(b, "cells") else [b.position]
                if (nx, ny) in cells and not b.passable:
                    blocked = True
                    break
            if blocked:
                continue
            if any(v.position == (nx, ny) for v in game.entities if v is not self):
                continue
            self.target_path = [(nx, ny)]
            self._move_step(game)
            return True
        logger.debug("Villager %s failed to wander from %s", self.id, self.position)
        return False

    def thought(self, game: "Game") -> str:
        if self.cooldown > 0:
            return "Waiting..."
        if self.state == "sleep":
            return "Sleeping"
        if self.state == "idle":
            return "Idle"
        if self.state == "gather":
            if self.target_resource:
                if self.position == self.target_resource:
                    return f"Gathering {self.resource_type.name.lower()}"
                if self.target_path:
                    return f"Heading to {self.resource_type.name.lower()} at {self.target_resource}"
                return "Stuck: no path to resource"
            return "Searching for resource"
        if self.state == "deliver":
            if self.position in game.storage_positions:
                return "Delivering"
            if self.target_path:
                return f"Returning to storage at {self.target_storage}"
            return "Stuck: no path to storage"
        if self.state == "build":
            if self.target_building:
                if self.position == self.target_building.position:
                    return f"Building {self.target_building.blueprint.name}"
                if self.target_path:
                    return f"Heading to build {self.target_building.blueprint.name}"
                return "Stuck: no path to site"
            return "Searching for build"
        return self.state

    # ---------------------------------------------------------------
    def age_one_day(self, game: "Game") -> None:
        self.age += 1
        previous = self.life_stage
        if self.age < 18:
            self.life_stage = LifeStage.CHILD
        elif self.age < 65:
            self.life_stage = LifeStage.ADULT
        elif self.age < 80:
            self.life_stage = LifeStage.ELDER
        else:
            self.life_stage = LifeStage.RETIRED
        if self.life_stage != previous:
            if self.life_stage is LifeStage.RETIRED:
                game.log_event(f"Villager {self.id} retired")
            else:
                game.log_event(
                    f"Villager {self.id} became {self.life_stage.name.lower()}"
                )
        self.carrying_capacity = (
            CARRY_CAPACITY
            if self.life_stage in (LifeStage.ADULT, LifeStage.ELDER)
            else CARRY_CAPACITY // 2
        )

    def update(self, game: "Game") -> None:
        # Always use the hierarchical pathfinder.  The previous behaviour only
        # enabled the optimised variant after 25k ticks which caused heavy CPU
        # load once several villagers were active early on.
        path_func = find_path_fast
        # Wake up at dawn
        if self.state == "sleep" and not game.world.is_night:
            self.asleep = False
            self.state = "idle"
            self.target_path = []
        # Head home when night falls
        if game.world.is_night and self.home and self.state != "sleep":
            path = path_func(
                self.position,
                self.home,
                game.map,
                game.buildings,
                search_limit=game.get_search_limit(),
            )
            self.target_path = path[1:]
            self.state = "sleep"
        if self.life_stage is LifeStage.RETIRED:
            for v in game.entities:
                if v is not self and abs(v.x - self.x) <= 1 and abs(v.y - self.y) <= 1:
                    v.adjust_mood(1)
            self.state = "retired"
            return
        if self.personality is Personality.SOCIAL:
            if any(
                v is not self and abs(v.x - self.x) <= 1 and abs(v.y - self.y) <= 1
                for v in game.entities
            ):
                self.adjust_mood(1)
        if self.cooldown > 0:
            self.cooldown -= 1
            return
        if self._avoid_nearby_villagers(game):
            return
        if self.state == "idle":
            if random.random() < 0.2:
                self._wander(game)
                return
            job = game.dispatch_job(self)
            if not job:
                self.adjust_mood(-1)
                return
            if job.type == "gather":
                resource_type = (
                    job.payload if isinstance(job.payload, TileType) else TileType.TREE
                )
                reserved = self.reservations.get(resource_type)
                if reserved:
                    tile = game.map.get_tile(*reserved)
                    if tile.resource_amount <= 0:
                        game.release_resource(reserved)
                        self.reservations.pop(resource_type, None)
                        reserved = None
                if reserved:
                    path = path_func(
                        self.position,
                        reserved,
                        game.map,
                        game.buildings,
                        search_limit=game.get_search_limit(),
                    )
                    self.resource_type = resource_type
                    self.target_resource = reserved
                    self.target_path = path[1:]
                    self.state = "gather"
                    return
                avoid = [
                    pos
                    for pos, (_, rt) in game.reservations.items()
                    if rt == resource_type
                ]
                pos, path = find_nearest_resource(
                    self.position,
                    resource_type,
                    game.map,
                    game.buildings,
                    search_limit=game.get_search_limit(),
                    avoid=avoid,
                    spacing=3,
                    area=10,
                )
                if pos is None or not game.reserve_resource(
                    pos, self.id, resource_type
                ):
                    self._wander(game)
                    return
                self.resource_type = resource_type
                self.target_resource = pos
                self.reservations[resource_type] = pos
                self.target_path = path[1:]
                self.state = "gather"
                return
            if job.type == "build":
                self.target_building = job.payload
                path = find_path_to_building_adjacent(
                    self.position,
                    self.target_building,
                    game.map,
                    game.buildings,
                    search_limit=game.get_search_limit(),
                )
                self.target_path = path[1:]
                if not self.target_path:
                    logger.debug(
                        "Villager %s could not path to build site at %s",
                        self.id,
                        self.target_building.position,
                    )
                self.state = "build"
                return
        if self.state == "gather":
            if self._move_step(game):
                return
            if self.target_resource and self.position != self.target_resource:
                if not self.target_path:
                    path = path_func(
                        self.position,
                        self.target_resource,
                        game.map,
                        game.buildings,
                        search_limit=game.get_search_limit(),
                    )
                    self.target_path = path[1:]
                if not self.target_path:
                    logger.debug(
                        "Villager %s could not path to resource at %s",
                        self.id,
                        self.target_resource,
                    )
                    if self.target_resource:
                        game.release_resource(self.target_resource)
                        self.reservations.pop(self.resource_type, None)
                    self.target_resource = None
                    self.state = "idle"
                    self._wander(game)
                return
            if self.target_resource and self.position == self.target_resource:
                tile = game.map.get_tile(*self.position)
                rate = 1
                for b in game.buildings:
                    if b.blueprint.name == "Quarry" and b.complete:
                        bx, by = b.position
                        if (
                            abs(bx - self.position[0]) <= 5
                            and abs(by - self.position[1]) <= 5
                        ):
                            rate = 2
                            break
                gained = tile.extract(rate)
                if self.resource_type is TileType.ROCK:
                    self.inventory["stone"] += gained
                else:
                    self.inventory["wood"] += gained
                self.adjust_mood(1)
                self.cooldown = self._action_delay(game, VILLAGER_ACTION_DELAY)
                if tile.resource_amount == 0:
                    game.release_resource(self.target_resource)
                    self.reservations.pop(self.resource_type, None)
                    self.target_resource = None
                    if sum(self.inventory.values()) > 0:
                        self.state = "deliver"
                    else:
                        self.state = "idle"
                    self.target_path = []
                elif self.is_full():
                    self.state = "deliver"
                    self.target_path = []
            return
        if self.state == "deliver":
            # Immediately deliver if we're already on a storage tile
            if self.position in game.storage_positions:
                for res in ("wood", "stone"):
                    if self.inventory.get(res, 0) > 0:
                        game.adjust_storage(res, self.inventory.get(res, 0))
                        self.inventory[res] = 0
                self.adjust_mood(1)
                self.cooldown = self._action_delay(game, VILLAGER_ACTION_DELAY)
                # Once enough wood has been stockpiled for the very first house,
                # stop gathering and allow a build job to be assigned.
                if (
                    game._count_buildings("House") == 0
                    and game.storage["wood"] >= game.house_threshold
                ):
                    if self.target_resource:
                        game.release_resource(self.target_resource)
                        self.reservations.pop(self.resource_type, None)
                    self.target_resource = None
                    self.resource_type = None
                    self.state = "idle"
                    self.target_path = []
                    return
                if (
                    self.target_resource
                    and game.map.get_tile(*self.target_resource).resource_amount > 0
                ):
                    path = path_func(
                        self.position,
                        self.target_resource,
                        game.map,
                        game.buildings,
                        search_limit=game.get_search_limit(),
                    )
                    self.target_path = path[1:]
                    self.state = "gather"
                else:
                    if self.target_resource:
                        game.release_resource(self.target_resource)
                        self.reservations.pop(self.resource_type, None)
                    self.target_resource = None
                    self.resource_type = None
                    self.state = "idle"
                    self.target_path = []
                return

            if not self.target_path:
                self.target_storage = game.nearest_storage(self.position)
                path = path_func(
                    self.position,
                    self.target_storage,
                    game.map,
                    game.buildings,
                    search_limit=game.get_search_limit(),
                )
                self.target_path = path[1:]
                if not self.target_path:
                    logger.debug(
                        "Villager %s could not path to storage at %s",
                        self.id,
                        self.target_storage,
                    )
                    if self.target_resource:
                        game.release_resource(self.target_resource)
                        self.reservations.pop(self.resource_type, None)
                        self.target_resource = None
                        self.resource_type = None
                    self.state = "idle"
                    self._wander(game)
                    return

            if self._move_step(game):
                return
        if self.state == "build":
            if self._move_step(game):
                return
            if (
                self.target_building
                and not self.target_path
                and (
                    abs(self.position[0] - self.target_building.position[0])
                    + abs(self.position[1] - self.target_building.position[1])
                    > 1
                )
            ):
                path = find_path_to_building_adjacent(
                    self.position,
                    self.target_building,
                    game.map,
                    game.buildings,
                    search_limit=game.get_search_limit(),
                )
                self.target_path = path[1:]
                if not self.target_path:
                    logger.debug(
                        "Villager %s lost path to build site at %s",
                        self.id,
                        self.target_building.position if self.target_building else None,
                    )
                    self.state = "idle"
                    self._wander(game)
                return
            if self.target_building and (
                abs(self.position[0] - self.target_building.position[0])
                + abs(self.position[1] - self.target_building.position[1])
                == 1
            ):
                self.target_building.progress += 1
                self.adjust_mood(1)
                self.cooldown = self._action_delay(game, VILLAGER_ACTION_DELAY)
                if self.target_building.complete:
                    self.target_building.passable = (
                        self.target_building.blueprint.passable
                    )
                    if self.target_building in game.build_queue:
                        game.build_queue.remove(self.target_building)
                    # Remove any queued build jobs for this now-complete building
                    game.jobs = [
                        j for j in game.jobs if j.payload is not self.target_building
                    ]
                    self.target_building.builder_id = None
                    if self.target_building.blueprint.name == "Storage":
                        game.storage_capacity += self.target_building.blueprint.capacity_bonus
                    if self.target_building.blueprint.name == "House":
                        game.schedule_spawn(self.target_building.position)
                else:
                    from .game import Job

                    game.jobs.append(Job("build", self.target_building))
                    # Stay in build state to continue working on the same building
                    return
                self.state = "idle"
        if self.state == "sleep":
            if self.position != self.home:
                if not self.target_path:
                    path = path_func(
                        self.position,
                        self.home,
                        game.map,
                        game.buildings,
                        search_limit=game.get_search_limit(),
                    )
                    self.target_path = path[1:]
                self._move_step(game)
            else:
                self.asleep = True
            return

    @property
    def x(self) -> int:
        return self.position[0]

    @property
    def y(self) -> int:
        return self.position[1]
