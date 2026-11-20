"""Integrated two-tier search adapted from Faaiz's supplied notebook.

Preserves his corridor -> neighbouring regions -> whole-map fallback strategy.
Integration changes: calls Faaiz's helpers on the same World as flat A*
"""
from __future__ import annotations

import heapq
import math
import time
from dataclasses import dataclass, field

from flat_astar import SearchResult, flat_astar
from worlds import connected_areas

from types import SimpleNamespace
import faaiz_two_tier_search as faaiz

@dataclass
class Hierarchy:
    area: dict
    members: dict
    centers: dict
    adj: dict
    preprocess_ms: float
    blocked: frozenset


@dataclass
class HierarchicalResult(SearchResult):
    abstract_expanded: int = 0
    preprocess_ms: float = 0.0
    region_path: list = field(default_factory=list)
    mode: str = "Chosen regions"
    attempts: int = 0
    allowed_nodes: set = field(default_factory=set)


def prepare_hierarchy(world, blocked=()):
    before = time.perf_counter()
    closed = frozenset(blocked)

    area = (connected_areas(world.adj, world.base_areas, closed)
            if world.kind == "grid" and closed else world.area)

    graph = SimpleNamespace(
        adj=world.adj, coords=world.coords, area=area
    )

    members, centers, adj = faaiz.build_region_graph(
        graph, closed, distance=world.distance
    )

    return Hierarchy(
        area, members, centers, adj,
        (time.perf_counter() - before) * 1000, closed
    )


def region_search(world, hierarchy, start, goal):
    s, g = hierarchy.area[start], hierarchy.area[goal]

    if s == g:
        return [s], 0

    return faaiz.region_search(
        hierarchy.centers, hierarchy.adj, s, g,
        distance=world.distance
    )

    def h(r):
        return world.distance(hierarchy.centers[r], hierarchy.centers[g])

    queue, scores, previous = [(h(s), 0.0, s)], {s: 0.0}, {}
    expanded = 0
    while queue:
        _, cost, region = heapq.heappop(queue)
        if cost > scores.get(region, math.inf) + 1e-9:
            continue
        expanded += 1
        if region == g:
            path = [g]
            while path[-1] in previous:
                path.append(previous[path[-1]])
            return path[::-1], expanded
        for nb, weight in hierarchy.adj[region].items():
            candidate = cost + weight
            if candidate + 1e-9 < scores.get(nb, math.inf):
                scores[nb] = candidate
                previous[nb] = region
                heapq.heappush(queue, (candidate + h(nb), candidate, nb))
    return [], expanded


def two_tier_search(world, start, goal, blocked=(), *, hierarchy=None, collect_trace=False):
    closed = frozenset(blocked)
    if hierarchy is None:
        hierarchy = prepare_hierarchy(world, closed)
    if hierarchy.blocked != closed:
        raise ValueError("The hierarchy and detailed search must use identical closures.")
    before = time.perf_counter()
    corridor, abstract = region_search(world, hierarchy, start, goal)
    total_expanded, traces, attempts = 0, [], 0
    selected = set(corridor)
    attempts_to_try = []
    if selected:
        attempts_to_try.append(("Chosen regions", selected))
        wider = set(selected)
        for r in selected:
            wider.update(hierarchy.adj[r])
        for r, neighbors in hierarchy.adj.items():
            if selected.intersection(neighbors):
                wider.add(r)
        if wider != selected:
            attempts_to_try.append(("Widened to neighbouring regions", wider))
    attempts_to_try.append(("Whole-map fallback", None))
    for mode, regions in attempts_to_try:
        attempts += 1
        allowed = None if regions is None else {
            n for region in regions for n in hierarchy.members[region]
        }
        attempt_trace = [] if collect_trace else None

        path, cost, expanded = faaiz.detailed_astar(
            world, start, goal, closed, allowed,
            heuristic=world.heuristic(goal), trace=attempt_trace
        )

        res = SearchResult(
            path is not None, path or [], cost, expanded,
            0.0, attempt_trace or []
        )
        total_expanded += res.nodes_expanded
        traces.extend(res.trace)
        if res.found or regions is None:
            return HierarchicalResult(
                res.found, res.path, res.cost_m, total_expanded,
                (time.perf_counter() - before) * 1000, traces,
                abstract, hierarchy.preprocess_ms, corridor, mode, attempts,
                set(world.adj) if allowed is None else allowed,
            )
    raise AssertionError("A whole-map fallback must always produce a result.")
