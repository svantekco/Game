from __future__ import annotations

from dataclasses import dataclass, field
import heapq
from typing import Dict, List, Optional, Tuple, Iterable, Set

from .map import GameMap
from .constants import TileType, SEARCH_LIMIT


@dataclass
class _ScaledMap:
    """Simple wrapper that presents a scaled view of a ``GameMap``."""

    base: GameMap
    factor: int

    @property
    def width(self) -> int:
        return self.base.width // self.factor

    @property
    def height(self) -> int:
        return self.base.height // self.factor

    def get_tile(self, x: int, y: int):
        return self.base.get_tile(x * self.factor, y * self.factor)


@dataclass(order=True)
class _PQNode:
    priority: float
    count: int
    position: Tuple[int, int] = field(compare=False)


def _heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    """Manhattan distance heuristic."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _neighbors(pos: Tuple[int, int], gmap: GameMap) -> Iterable[Tuple[int, int]]:
    x, y = pos
    if x > 0:
        yield (x - 1, y)
    if x < gmap.width - 1:
        yield (x + 1, y)
    if y > 0:
        yield (x, y - 1)
    if y < gmap.height - 1:
        yield (x, y + 1)


def _is_passable(
    pos: Tuple[int, int], gmap: GameMap, buildings: Iterable[object]
) -> bool:
    """Check if the tile at ``pos`` can be traversed."""

    x, y = pos
    tile = gmap.get_tile(x, y)
    if not tile.passable:
        return False

    for b in buildings:
        # Buildings may span multiple cells via a ``cells`` helper
        cells: Iterable[Tuple[int, int]]
        if hasattr(b, "cells"):
            cells = getattr(b, "cells")()
        else:
            bx, by = getattr(b, "position", (None, None))
            cells = [(bx, by)]
        for cx, cy in cells:
            if cx == x and cy == y and not getattr(b, "passable", False):
                return False

    return True


def _is_road(pos: Tuple[int, int], buildings: Iterable[object]) -> bool:
    """Return True if a completed Road occupies ``pos``."""
    x, y = pos
    for b in buildings:
        if (
            getattr(b, "position", None) == (x, y)
            and getattr(b, "blueprint", None) is not None
            and getattr(b.blueprint, "name", "") == "Road"
            and getattr(b, "complete", False)
        ):
            return True
    return False


def _step_cost(
    pos: Tuple[int, int], gmap: GameMap, buildings: Iterable[object]
) -> float:
    """Return traversal cost for ``pos`` factoring in roads."""
    return 0.5 if _is_road(pos, buildings) else 1.0


def find_path(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    gmap: GameMap,
    buildings: Iterable[object] | None = None,
) -> List[Tuple[int, int]]:
    """A* pathfinding from start to goal. Returns list of waypoints."""

    if buildings is None:
        buildings = []

    open_heap: List[_PQNode] = []
    heapq.heappush(open_heap, _PQNode(0.0, 0, start))
    g_score: Dict[Tuple[int, int], float] = {start: 0.0}
    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    closed: Set[Tuple[int, int]] = set()
    counter = 1

    while open_heap:
        node = heapq.heappop(open_heap)
        current = node.position
        if current == goal:
            # reconstruct path
            path: List[Tuple[int, int]] = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path
        if current in closed:
            continue
        closed.add(current)

        for n in _neighbors(current, gmap):
            if not _is_passable(n, gmap, buildings):
                continue
            tentative_g = g_score[current] + _step_cost(n, gmap, buildings)
            if tentative_g < g_score.get(n, float("inf")):
                came_from[n] = current
                g_score[n] = tentative_g
                f_score = tentative_g + _heuristic(n, goal)
                heapq.heappush(open_heap, _PQNode(f_score, counter, n))
                counter += 1

    return []  # no path found


def find_nearest_resource(
    start: Tuple[int, int],
    resource_type: TileType,
    gmap: GameMap,
    buildings: Iterable[object] | None = None,
    *,
    search_limit: int = SEARCH_LIMIT,
) -> Tuple[Optional[Tuple[int, int]], List[Tuple[int, int]]]:
    """Find the closest tile of the given resource type and a path to it."""

    if buildings is None:
        buildings = []

    open_heap: List[_PQNode] = []
    heapq.heappush(open_heap, _PQNode(0.0, 0, start))
    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    g_score: Dict[Tuple[int, int], float] = {start: 0.0}
    explored = 0
    counter = 1

    while open_heap:
        node = heapq.heappop(open_heap)
        current = node.position

        explored += 1
        if explored > search_limit:
            break

        tile = gmap.get_tile(*current)
        if tile.type is resource_type and tile.resource_amount > 0:
            found = current
            path: List[Tuple[int, int]] = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return found, path

        for n in _neighbors(current, gmap):
            if not _is_passable(n, gmap, buildings):
                continue
            tentative_g = g_score[current] + _step_cost(n, gmap, buildings)
            if tentative_g < g_score.get(n, float("inf")):
                g_score[n] = tentative_g
                came_from[n] = current
                heapq.heappush(open_heap, _PQNode(tentative_g, counter, n))
                counter += 1

    return None, []


def find_path_hierarchical(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    gmap: GameMap,
    buildings: Iterable[object] | None = None,
    *,
    coarse_distance: int = 50,
    step: int = 4,
) -> List[Tuple[int, int]]:
    """Hierarchical A* pathfinding with a coarse pre-pass.

    For long distance travel the search space can explode.  This helper first
    plans a route on a down-scaled version of the map to get close to the
    target before running the normal ``find_path`` for the fine grained steps.
    """

    if buildings is None:
        buildings = []

    dx = abs(goal[0] - start[0])
    dy = abs(goal[1] - start[1])
    if max(dx, dy) <= coarse_distance or step <= 1:
        return find_path(start, goal, gmap, buildings)

    scaled = _ScaledMap(gmap, step)
    coarse_start = (start[0] // step, start[1] // step)
    coarse_goal = (goal[0] // step, goal[1] // step)

    coarse_path = find_path(coarse_start, coarse_goal, scaled, buildings)
    if not coarse_path:
        return []

    path: List[Tuple[int, int]] = []
    current = start
    for cp in coarse_path[1:]:
        target = (cp[0] * step, cp[1] * step)
        segment = find_path(current, target, gmap, buildings)
        if not segment:
            return []
        if path and segment[0] == path[-1]:
            path.extend(segment[1:])
        else:
            path.extend(segment)
        current = target

    final_segment = find_path(current, goal, gmap, buildings)
    if not final_segment:
        return []
    if path and final_segment[0] == path[-1]:
        path.extend(final_segment[1:])
    else:
        path.extend(final_segment)

    return path


def find_path_to_building_adjacent(
    start: Tuple[int, int],
    building: object,
    gmap: GameMap,
    buildings: Iterable[object] | None = None,
) -> List[Tuple[int, int]]:
    """Return a path to a passable tile adjacent to ``building``."""

    if buildings is None:
        buildings = []

    if hasattr(building, "cells"):
        cells = building.cells()
    else:
        cells = [getattr(building, "position", (0, 0))]

    candidates: Set[Tuple[int, int]] = set()
    for bx, by in cells:
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            cx, cy = bx + dx, by + dy
            if 0 <= cx < gmap.width and 0 <= cy < gmap.height:
                if _is_passable((cx, cy), gmap, buildings):
                    candidates.add((cx, cy))

    best: List[Tuple[int, int]] = []
    for cand in candidates:
        path = find_path(start, cand, gmap, buildings)
        if path and (not best or len(path) < len(best)):
            best = path

    return best
