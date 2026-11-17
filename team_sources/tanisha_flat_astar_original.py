"""Flat A* baseline for CSCI218 Project H.

Compatible with Humna's `RoadMap` (osm_map.py):
    road_map.adj: node -> {neighbor: distance_in_metres}
    road_map.coords: node -> (latitude, longitude)

Unlike the two-tier method, this algorithm does not use hub_node or area.
Blocked edges are directed (u, v) pairs, matching RoadMap.edges_near().
"""
from __future__ import annotations

from dataclasses import dataclass
import heapq
import math
import time
from typing import Hashable, Mapping

Node = Hashable


@dataclass
class SearchResult:
    found: bool
    path: list[Node]
    cost_m: float | None
    nodes_expanded: int
    runtime_ms: float

    def as_dict(self) -> dict:
        return {"found": self.found, "path": self.path, "cost_m": self.cost_m,
                "nodes_expanded": self.nodes_expanded, "runtime_ms": self.runtime_ms}


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance in metres, used as a lower-bound estimate."""
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    x = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    return 2 * 6371000.0 * math.asin(min(1.0, math.sqrt(x)))


def flat_astar(road_map, start: Node, goal: Node, blocked=(), *, use_heuristic=True) -> SearchResult:
    """Find the minimum-distance route on the *whole* directed graph.

    Args:
        road_map: object containing `adj` and `coords` attributes.
        start, goal: road node IDs (use road_map.hub_node[name] for named hubs).
        blocked: iterable of directed (from_node, to_node) closed road edges.
        use_heuristic: True uses haversine; False runs Dijkstra-like search.

    Important: A* shortest-path optimality assumes that every edge weight is
    >= the geographic straight-line distance between its endpoints. This is
    true for distance-weighted real road segments with valid coordinates.
    For synthetic graphs with unrelated weights, set use_heuristic=False.
    """
    t0 = time.perf_counter()
    adj = road_map.adj
    coords = road_map.coords
    if start not in adj or goal not in adj:
        raise ValueError("start and goal must be nodes in road_map.adj")
    if use_heuristic and (start not in coords or goal not in coords):
        raise ValueError("Coordinates missing for start or goal")

    blocked_set = set(blocked)
    if start == goal:
        return SearchResult(True, [start], 0.0, 0, (time.perf_counter() - t0) * 1000)

    def h(n):
        return haversine_m(coords[n], coords[goal]) if use_heuristic else 0.0

    best_g = {start: 0.0}
    previous = {}
    # Include g score so outdated entries can be ignored safely.
    queue = [(h(start), 0.0, 0, start)]
    counter = 1
    expanded = 0
    while queue:
        _, g, _, node = heapq.heappop(queue)
        if g > best_g[node] + 1e-9:
            continue
        expanded += 1
        if node == goal:
            path = [goal]
            while path[-1] in previous:
                path.append(previous[path[-1]])
            path.reverse()
            return SearchResult(True, path, g, expanded,
                                (time.perf_counter() - t0) * 1000)
        for neighbor, distance_m in adj[node].items():
            if (node, neighbor) in blocked_set:
                continue
            if not math.isfinite(distance_m) or distance_m < 0:
                raise ValueError(f"Invalid edge cost {node}->{neighbor}: {distance_m}")
            candidate = g + distance_m
            if candidate + 1e-9 < best_g.get(neighbor, math.inf):
                best_g[neighbor] = candidate
                previous[neighbor] = node
                heapq.heappush(queue, (candidate + h(neighbor), candidate, counter, neighbor))
                counter += 1
    return SearchResult(False, [], None, expanded, (time.perf_counter() - t0) * 1000)


def route_cost(road_map, path: list[Node], blocked=()) -> float:
    """Independently calculate cost and validate that all path edges are open."""
    closed = set(blocked)
    cost = 0.0
    for u, v in zip(path, path[1:]):
        if (u, v) in closed or v not in road_map.adj.get(u, {}):
            raise ValueError(f"Path contains missing/closed edge: {u}->{v}")
        cost += road_map.adj[u][v]
    return cost
