from __future__ import annotations

from dataclasses import dataclass, field
import heapq
import random
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


def _nearest_passable(
    start: Tuple[int, int], gmap: GameMap, search_limit: int = SEARCH_LIMIT
) -> Tuple[int, int]:
    """Return ``start`` if passable else the closest passable tile."""
    if gmap.get_tile(*start).passable:
        return start

    from collections import deque

    q = deque([start])
    visited = {start}
    explored = 0
    while q and explored < search_limit:
        x, y = q.popleft()
        explored += 1
        for n in _neighbors((x, y), gmap):
            if n in visited:
                continue
            visited.add(n)
            if gmap.get_tile(*n).passable:
                return n
            q.append(n)
    return start


def find_path(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    gmap: GameMap,
    buildings: Iterable[object] | None = None,
    *,
    search_limit: int = SEARCH_LIMIT,
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

    explored = 0
    while open_heap:
        node = heapq.heappop(open_heap)
        current = node.position
        explored += 1
        if explored > search_limit:
            break
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


def find_path_fast(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    gmap: GameMap,
    buildings: Iterable[object] | None = None,
    *,
    search_limit: int = SEARCH_LIMIT,
    coarse_distance: int = 50,
    step: int = 4,
) -> List[Tuple[int, int]]:
    """Return a path using hierarchical search for long distances."""

    if buildings is None:
        buildings = []

    dx = abs(goal[0] - start[0])
    dy = abs(goal[1] - start[1])
    if max(dx, dy) > coarse_distance:
        return find_path_hierarchical(
            start,
            goal,
            gmap,
            buildings,
            coarse_distance=coarse_distance,
            step=step,
            search_limit=search_limit,
        )

    return find_path(start, goal, gmap, buildings, search_limit=search_limit)


def _map_cache(
    gmap: GameMap,
) -> Dict[Tuple[TileType, int, int, int], List[List[Tuple[int, int]]]]:
    """Return the cluster cache dictionary attached to ``gmap``."""

    cache = getattr(gmap, "_cluster_cache", None)
    if cache is None:
        cache = {}
        setattr(gmap, "_cluster_cache", cache)
    return cache


def _cluster_key(
    gmap: GameMap, resource: TileType, center: Tuple[int, int], radius: int
) -> Tuple[TileType, int, int, int]:
    """Return a stable key for a region around ``center``."""

    return (
        resource,
        center[0] // (radius * 2),
        center[1] // (radius * 2),
        radius,
    )


def _compute_clusters(
    gmap: GameMap, resource: TileType, center: Tuple[int, int], radius: int
) -> List[List[Tuple[int, int]]]:
    """Return clusters of ``resource`` tiles within ``radius`` of ``center``."""

    min_x = max(0, center[0] - radius)
    max_x = min(gmap.width - 1, center[0] + radius)
    min_y = max(0, center[1] - radius)
    max_y = min(gmap.height - 1, center[1] + radius)

    visited: Set[Tuple[int, int]] = set()
    clusters: List[List[Tuple[int, int]]] = []

    for x in range(min_x, max_x + 1):
        for y in range(min_y, max_y + 1):
            pos = (x, y)
            if pos in visited:
                continue
            tile = gmap.get_tile(x, y)
            if tile.type is not resource or tile.resource_amount <= 0:
                continue
            cluster: List[Tuple[int, int]] = []
            stack = [pos]
            visited.add(pos)
            while stack:
                cx, cy = stack.pop()
                cluster.append((cx, cy))
                for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                    nx, ny = cx + dx, cy + dy
                    npos = (nx, ny)
                    if (
                        min_x <= nx <= max_x
                        and min_y <= ny <= max_y
                        and npos not in visited
                    ):
                        t = gmap.get_tile(nx, ny)
                        if t.type is resource and t.resource_amount > 0:
                            visited.add(npos)
                            stack.append(npos)
            clusters.append(cluster)

    return clusters


def _get_clusters(
    gmap: GameMap, resource: TileType, center: Tuple[int, int], radius: int
) -> List[List[Tuple[int, int]]]:
    """Retrieve cached clusters near ``center`` or compute them."""

    cache = _map_cache(gmap)
    key = _cluster_key(gmap, resource, center, radius)
    if key not in cache:
        clusters: List[List[Tuple[int, int]]] = []
        pre = getattr(getattr(gmap, "precomputed_clusters", None), "get", lambda _: [])(
            resource
        )
        for cx, cy in pre:
            if abs(cx - center[0]) <= radius * 2 and abs(cy - center[1]) <= radius * 2:
                clusters.append([(cx, cy)])
        clusters.extend(_compute_clusters(gmap, resource, center, radius))
        cache[key] = clusters
    return cache[key]


def _nearest_resource_bfs(
    start: Tuple[int, int],
    resource_type: TileType,
    gmap: GameMap,
    buildings: Iterable[object],
    search_limit: int,
) -> Tuple[Optional[Tuple[int, int]], List[Tuple[int, int]]]:
    """Fallback BFS search used when clustering fails."""

    from collections import deque

    q = deque([start])
    came_from: Dict[Tuple[int, int], Tuple[int, int] | None] = {start: None}
    explored = 0

    while q and explored < search_limit:
        current = q.popleft()
        explored += 1

        tile = gmap.get_tile(*current)
        if tile.type is resource_type and tile.resource_amount > 0:
            found = current
            path: List[Tuple[int, int]] = [current]
            while came_from[current] is not None:
                current = came_from[current]  # type: ignore[index]
                path.append(current)
            path.reverse()
            return found, path

        neighbors = list(_neighbors(current, gmap))
        random.shuffle(neighbors)
        for n in neighbors:
            if n in came_from:
                continue
            if not _is_passable(n, gmap, buildings):
                continue
            came_from[n] = current
            q.append(n)

    return None, []


def find_nearest_resource(
    start: Tuple[int, int],
    resource_type: TileType,
    gmap: GameMap,
    buildings: Iterable[object] | None = None,
    *,
    search_limit: int = SEARCH_LIMIT,
    cluster_radius: int = 25,
) -> Tuple[Optional[Tuple[int, int]], List[Tuple[int, int]]]:
    """Find the closest tile of ``resource_type`` using cached clusters."""

    if buildings is None:
        buildings = []

    clusters = _get_clusters(gmap, resource_type, start, cluster_radius)

    best_path: List[Tuple[int, int]] = []
    best_target: Optional[Tuple[int, int]] = None

    for cluster in clusters:
        # pick the closest tile in this cluster
        candidate = min(
            cluster,
            key=lambda p: abs(p[0] - start[0]) + abs(p[1] - start[1]),
        )
        path = find_path(start, candidate, gmap, buildings, search_limit=search_limit)
        if path and (not best_path or len(path) < len(best_path)):
            best_path = path
            best_target = candidate

    if best_target is not None:
        return best_target, best_path

    # Fallback to BFS if no cluster produced a viable path
    return _nearest_resource_bfs(start, resource_type, gmap, buildings, search_limit)


def find_path_hierarchical(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    gmap: GameMap,
    buildings: Iterable[object] | None = None,
    *,
    coarse_distance: int = 50,
    step: int = 4,
    search_limit: int = SEARCH_LIMIT,
) -> List[Tuple[int, int]]:
    """Hierarchical A* pathfinding with a coarse pre-pass.

    For long distance travel the search space can explode.  This helper first
    plans a route on a down-scaled version of the map to get close to the
    target before running the normal ``find_path`` for the fine grained steps.
    """

    if buildings is None:
        buildings = []

    start_pass = _nearest_passable(start, gmap, search_limit)
    goal_pass = _nearest_passable(goal, gmap, search_limit)

    dx = abs(goal_pass[0] - start_pass[0])
    dy = abs(goal_pass[1] - start_pass[1])
    if max(dx, dy) <= coarse_distance or step <= 1:
        path = find_path(
            start_pass, goal_pass, gmap, buildings, search_limit=search_limit
        )
        if start_pass != start:
            prefix = find_path(
                start, start_pass, gmap, buildings, search_limit=search_limit
            )
            if prefix:
                path = prefix[:-1] + path
        if goal_pass != goal:
            suffix = find_path(
                goal_pass, goal, gmap, buildings, search_limit=search_limit
            )
            if suffix:
                path = path + suffix[1:]
        return path

    scaled = _ScaledMap(gmap, step)
    coarse_start = (start_pass[0] // step, start_pass[1] // step)
    coarse_goal = (goal_pass[0] // step, goal_pass[1] // step)

    coarse_path = find_path(
        coarse_start, coarse_goal, scaled, buildings, search_limit=search_limit
    )
    if not coarse_path:
        return []

    path: List[Tuple[int, int]] = []
    current = start_pass
    for cp in coarse_path[1:]:
        target = (cp[0] * step, cp[1] * step)
        segment = find_path(current, target, gmap, buildings, search_limit=search_limit)
        if not segment:
            return []
        if path and segment[0] == path[-1]:
            path.extend(segment[1:])
        else:
            path.extend(segment)
        current = target

    final_segment = find_path(
        current, goal_pass, gmap, buildings, search_limit=search_limit
    )
    if not final_segment:
        return []
    if path and final_segment[0] == path[-1]:
        path.extend(final_segment[1:])
    else:
        path.extend(final_segment)

    if start_pass != start:
        prefix = find_path(
            start, start_pass, gmap, buildings, search_limit=search_limit
        )
        if prefix:
            path = prefix[:-1] + path
    if goal_pass != goal:
        suffix = find_path(goal_pass, goal, gmap, buildings, search_limit=search_limit)
        if suffix:
            path = path + suffix[1:]
    return path


def find_path_to_building_adjacent(
    start: Tuple[int, int],
    building: object,
    gmap: GameMap,
    buildings: Iterable[object] | None = None,
    *,
    search_limit: int = SEARCH_LIMIT,
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
        path = find_path_fast(
            start,
            cand,
            gmap,
            buildings,
            search_limit=search_limit,
            coarse_distance=50,
            step=4,
        )
        if path and (not best or len(path) < len(best)):
            best = path

    return best
