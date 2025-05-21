from __future__ import annotations

import random
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
)
from .pathfinding import find_nearest_resource, find_path


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

    # ---------------------------------------------------------------
    def is_full(self) -> bool:
        return sum(self.inventory.values()) >= self.carrying_capacity

    def _apply_tool_bonus(self, game: "Game", delay: int) -> int:
        for b in game.buildings:
            if b.blueprint.name == "Blacksmith" and b.complete:
                bx, by = b.position
                if abs(bx - self.position[0]) <= 5 and abs(by - self.position[1]) <= 5:
                    return max(1, delay // 2)
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

    def _action_delay(self, game: "Game", base_delay: int) -> int:
        delay = self._apply_tool_bonus(game, base_delay)
        delay = int(
            delay
            * self._personality_delay_factor()
            * self._mood_delay_factor()
            * self._life_stage_delay_factor()
        )
        return max(1, delay)

    def adjust_mood(self, delta: int) -> None:
        levels = [Mood.SAD, Mood.NEUTRAL, Mood.HAPPY]
        idx = levels.index(self.mood)
        idx = max(0, min(len(levels) - 1, idx + delta))
        self.mood = levels[idx]

    def _move_step(self, game: "Game") -> bool:
        if not self.target_path:
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

    def thought(self, game: "Game") -> str:
        if self.cooldown > 0:
            return "Waiting..."
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
        if self.state == "sleeping":
            return "Sleeping"
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
            CARRY_CAPACITY if self.life_stage in (LifeStage.ADULT, LifeStage.ELDER) else CARRY_CAPACITY // 2
        )

    def update(self, game: "Game") -> None:
        if game.world.is_night:
            self.target_resource = None
            self.target_building = None
            if self.home and self.position != self.home:
                if not self.target_path:
                    path = find_path(self.position, self.home, game.map, game.buildings)
                    self.target_path = path[1:]
                self._move_step(game)
            else:
                self.state = "sleeping"
                self.asleep = True
                self.target_path = []
            return
        if self.asleep:
            self.asleep = False
            self.state = "idle"
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
        if self.state == "idle":
            job = game.dispatch_job(self)
            if not job:
                self.adjust_mood(-1)
                return
            if job.type == "gather":
                resource_type = (
                    job.payload if isinstance(job.payload, TileType) else TileType.TREE
                )
                pos, path = find_nearest_resource(
                    self.position,
                    resource_type,
                    game.map,
                    game.buildings,
                    search_limit=game.get_search_limit(),
                )
                if pos is None:
                    return
                self.resource_type = resource_type
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
            if self._move_step(game):
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
                if self.is_full() or tile.resource_amount == 0:
                    self.state = "deliver"
                    self.target_path = []
            return
        if self.state == "deliver":
            if not self.target_path:
                self.target_storage = game.nearest_storage(self.position)
                path = find_path(
                    self.position, self.target_storage, game.map, game.buildings
                )
                self.target_path = path[1:]
            if self._move_step(game):
                return
            if self.position in game.storage_positions:
                for res in ("wood", "stone"):
                    if self.inventory.get(res, 0) > 0:
                        game.adjust_storage(res, self.inventory.get(res, 0))
                        self.inventory[res] = 0
                self.adjust_mood(1)
                self.cooldown = self._action_delay(game, VILLAGER_ACTION_DELAY)
                self.state = "idle"
        if self.state == "build":
            if self._move_step(game):
                return
            if self.target_building and self.position == self.target_building.position:
                self.target_building.progress += 1
                self.adjust_mood(1)
                self.cooldown = self._action_delay(game, VILLAGER_ACTION_DELAY)
                if self.target_building.complete:
                    self.target_building.passable = False
                    if self.target_building in game.build_queue:
                        game.build_queue.remove(self.target_building)
                    if self.target_building.blueprint.name == "House":
                        game.schedule_spawn(self.target_building.position)
                else:
                    from .game import Job

                    game.jobs.append(Job("build", self.target_building))
                    # Stay in build state to continue working on the same building
                    return
                self.state = "idle"

    @property
    def x(self) -> int:
        return self.position[0]

    @property
    def y(self) -> int:
        return self.position[1]
