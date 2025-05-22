from __future__ import annotations

import heapq
import logging
import random
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple

from .constants import SEARCH_LIMIT, TileType
from .map import GameMap

logger = logging.getLogger(__name__)


@dataclass(order=True)
class _Node:
    f: int
    count: int
    pos: Tuple[int, int] = field(compare=False)


def _neighbors(pos: Tuple[int, int], gmap: GameMap) -> Iterable[Tuple[int, int]]:
    x, y = pos
    neighbors: List[Tuple[int, int]] = []
    if x > 0:
        neighbors.append((x - 1, y))
    if x < gmap.width - 1:
        neighbors.append((x + 1, y))
    if y > 0:
        neighbors.append((x, y - 1))
    if y < gmap.height - 1:
        neighbors.append((x, y + 1))
    random.shuffle(neighbors)
    for n in neighbors:
        yield n


def _passable(pos: Tuple[int, int], gmap: GameMap, buildings: Iterable[object]) -> bool:
    tile = gmap.get_tile(*pos)
    if not tile.passable:
        return False
    for b in buildings:
        cells = b.cells() if hasattr(b, "cells") else [getattr(b, "position", (0, 0))]
        if pos in cells and not getattr(b, "passable", False):
            return False
    return True


def find_path(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    gmap: GameMap,
    buildings: Iterable[object] | None = None,
    *,
    search_limit: int = SEARCH_LIMIT,
) -> List[Tuple[int, int]]:
    """Simple A* pathfinding returning a list of waypoints."""
    if buildings is None:
        buildings = []
    open_list: List[_Node] = []
    heapq.heappush(open_list, _Node(0, 0, start))
    came: Dict[Tuple[int, int], Tuple[int, int]] = {}
    g_score: Dict[Tuple[int, int], int] = {start: 0}
    closed: Set[Tuple[int, int]] = set()
    count = 1
    explored = 0

    while open_list and explored < search_limit:
        node = heapq.heappop(open_list)
        current = node.pos
        if current == goal:
            path = [current]
            while current in came:
                current = came[current]
                path.append(current)
            path.reverse()
            return path
        if current in closed:
            continue
        closed.add(current)
        explored += 1
        for n in _neighbors(current, gmap):
            if not _passable(n, gmap, buildings):
                continue
            tentative = g_score[current] + 1
            if tentative < g_score.get(n, 1_000_000):
                came[n] = current
                g_score[n] = tentative
                f = tentative + abs(goal[0] - n[0]) + abs(goal[1] - n[1])
                heapq.heappush(open_list, _Node(f, count, n))
                count += 1

    logger.debug("find_path failed from %s to %s after %d", start, goal, explored)
    return []


def find_path_fast(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    gmap: GameMap,
    buildings: Iterable[object] | None = None,
    *,
    search_limit: int = SEARCH_LIMIT,
    **_: int,
) -> List[Tuple[int, int]]:
    """Compatibility wrapper for the previous fast pathfinder."""
    return find_path(start, goal, gmap, buildings, search_limit=search_limit)


def find_path_hierarchical(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    gmap: GameMap,
    buildings: Iterable[object] | None = None,
    *,
    coarse_distance: int = 0,
    step: int = 1,
    search_limit: int = SEARCH_LIMIT,
) -> List[Tuple[int, int]]:
    """Simplified hierarchical pathfinder using a single A* pass."""
    return find_path(start, goal, gmap, buildings, search_limit=search_limit)


def find_path_to_building_adjacent(
    start: Tuple[int, int],
    building: object,
    gmap: GameMap,
    buildings: Iterable[object] | None = None,
    *,
    search_limit: int = SEARCH_LIMIT,
) -> List[Tuple[int, int]]:
    if buildings is None:
        buildings = []
    cells = building.cells() if hasattr(building, "cells") else [building.position]
    candidates: Set[Tuple[int, int]] = set()
    for bx, by in cells:
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            cx, cy = bx + dx, by + dy
            if 0 <= cx < gmap.width and 0 <= cy < gmap.height:
                if _passable((cx, cy), gmap, buildings):
                    candidates.add((cx, cy))
    best: List[Tuple[int, int]] = []
    for cand in candidates:
        path = find_path(start, cand, gmap, buildings, search_limit=search_limit)
        if path and (not best or len(path) < len(best)):
            best = path
    return best


def find_nearest_resource(
    start: Tuple[int, int],
    resource_type: TileType,
    gmap: GameMap,
    buildings: Iterable[object] | None = None,
    *,
    search_limit: int = SEARCH_LIMIT,
    avoid: Iterable[Tuple[int, int]] | None = None,
    spacing: int = 0,
    area: int = 10,
) -> Tuple[Optional[Tuple[int, int]], List[Tuple[int, int]]]:
    """Return the nearest tile of ``resource_type`` using BFS."""
    if buildings is None:
        buildings = []
    if avoid is None:
        avoid = []
    avoid_set = set(avoid)

    from collections import deque

    if spacing > 0:
        half = area // 2
        q = deque([(start, [start])])
        visited = {start}
        while q:
            pos, path = q.popleft()
            if (
                abs(pos[0] - start[0]) > half
                or abs(pos[1] - start[1]) > half
            ):
                continue
            tile = gmap.get_tile(*pos)
            if (
                tile.type is resource_type
                and tile.resource_amount > 0
                and pos not in avoid_set
                and all(
                    abs(pos[0] - ax) + abs(pos[1] - ay) >= spacing
                    for ax, ay in avoid_set
                )
            ):
                return pos, path
            for n in _neighbors(pos, gmap):
                if n in visited or not _passable(n, gmap, buildings):
                    continue
                visited.add(n)
                q.append((n, path + [n]))

    q = deque([(start, [start])])
    visited = {start}
    explored = 0

    while q and explored < search_limit:
        pos, path = q.popleft()
        tile = gmap.get_tile(*pos)
        if (
            tile.type is resource_type
            and tile.resource_amount > 0
            and pos not in avoid_set
        ):
            return pos, path
        explored += 1
        for n in _neighbors(pos, gmap):
            if n in visited or not _passable(n, gmap, buildings):
                continue
            visited.add(n)
            q.append((n, path + [n]))

    logger.debug("find_nearest_resource exhausted search from %s", start)
    return None, []


