from __future__ import annotations

from dataclasses import dataclass, field
import heapq
from typing import Dict, List, Optional, Tuple, Iterable, Set

from .map import GameMap
from .constants import TileType


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
            tentative_g = g_score[current] + 1
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
) -> Tuple[Optional[Tuple[int, int]], List[Tuple[int, int]]]:
    """Find the closest tile of the given resource type and a path to it."""

    if buildings is None:
        buildings = []

    from collections import deque

    frontier = deque([start])
    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    visited: Set[Tuple[int, int]] = {start}

    while frontier:
        current = frontier.popleft()
        tile = gmap.get_tile(*current)
        if tile.type is resource_type and tile.resource_amount > 0:
            path: List[Tuple[int, int]] = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return current, path

        for n in _neighbors(current, gmap):
            if n in visited:
                continue
            if not _is_passable(n, gmap, buildings):
                continue
            visited.add(n)
            frontier.append(n)
            came_from[n] = current

    return None, []
