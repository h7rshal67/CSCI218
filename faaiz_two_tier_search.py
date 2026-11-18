"""
faaiz_two_tier_search.py  -  Faaiz's two-tier search, rewritten for Humna's map.

Why this file exists
--------------------
Faaiz's earlier notebook built its own graph (downloaded with OSMnx, regions made
with K-Means). Humna's map uses a different representation, so the two parts
could not be run on the same data. This version works directly on Humna's
`RoadMap` (osm_map.py) and uses ONLY the fields it already provides:

    road_map.adj     node -> {neighbour: metres}      (directed roads)
    road_map.coords  node -> (lat, lon)
    road_map.area    node -> hub name (the region of that node)

Closed roads are directed (u, v) pairs, exactly what RoadMap.edges_near() returns.

Strategy (same as the original notebook)
----------------------------------------
Level 1: A* over the region graph picks the regions to pass through.
Level 2: A* on the real roads, using only nodes inside those regions.
If that fails -> widen to neighbouring regions -> finally search the whole map.
"""
import heapq
import math
import time

from osm_map import haversine_m


# ---------------------------------------------------------------- level 1 ----
def build_region_graph(road_map, blocked=frozenset()):
    """Return (members, centers, region_adj) built from Humna's road_map.area."""
    members = {}
    for node, region in road_map.area.items():
        members.setdefault(region, []).append(node)

    centers = {
        r: (sum(road_map.coords[n][0] for n in ns) / len(ns),
            sum(road_map.coords[n][1] for n in ns) / len(ns))
        for r, ns in members.items()
    }

    region_adj = {r: {} for r in members}
    for u, neighbours in road_map.adj.items():
        for v in neighbours:
            if (u, v) in blocked:
                continue                      # closed roads never join regions
            a, b = road_map.area[u], road_map.area[v]
            if a != b:
                region_adj[a][b] = haversine_m(*centers[a], *centers[b])
    return members, centers, region_adj


def region_search(centers, region_adj, start_region, goal_region):
    """A* over regions. Returns (list of regions, nodes expanded)."""
    if start_region == goal_region:
        return [start_region], 0

    def h(r):
        return haversine_m(*centers[r], *centers[goal_region])

    heap = [(h(start_region), 0.0, start_region)]
    best, came, expanded = {start_region: 0.0}, {}, 0
    while heap:
        _, g, r = heapq.heappop(heap)
        if g > best.get(r, math.inf):
            continue
        expanded += 1
        if r == goal_region:
            path = [r]
            while path[-1] in came:
                path.append(came[path[-1]])
            return path[::-1], expanded
        for nb, w in region_adj[r].items():
            ng = g + w
            if ng < best.get(nb, math.inf):
                best[nb], came[nb] = ng, r
                heapq.heappush(heap, (ng + h(nb), ng, nb))
    return [], expanded


# ---------------------------------------------------------------- level 2 ----
def detailed_astar(road_map, start, goal, blocked=frozenset(), allowed=None):
    """A* on the real roads. allowed = set of nodes it may use (None = all)."""
    goal_pos = road_map.coords[goal]

    def h(n):
        return haversine_m(*road_map.coords[n], *goal_pos)

    heap = [(h(start), 0.0, start)]
    best, came, expanded = {start: 0.0}, {}, 0
    while heap:
        _, g, u = heapq.heappop(heap)
        if g > best.get(u, math.inf):
            continue
        expanded += 1
        if u == goal:
            path = [u]
            while path[-1] in came:
                path.append(came[path[-1]])
            return path[::-1], g, expanded
        for v, w in road_map.adj[u].items():
            if (u, v) in blocked or (allowed is not None and v not in allowed):
                continue
            ng = g + w
            if ng < best.get(v, math.inf):
                best[v], came[v] = ng, u
                heapq.heappush(heap, (ng + h(v), ng, v))
    return None, None, expanded


# ------------------------------------------------------------ the two tiers ----
def two_tier_search(road_map, start, goal, blocked=()):
    """Faaiz's two-tier search on Humna's RoadMap.

    Returns a dict: found, path, cost_m, nodes_expanded (all attempts counted),
    runtime_ms, region_path, mode.
    """
    t0 = time.perf_counter()
    blocked = frozenset(blocked)
    members, centers, region_adj = build_region_graph(road_map, blocked)

    corridor, region_expanded = region_search(
        centers, region_adj, road_map.area[start], road_map.area[goal])
    total_expanded = region_expanded

    attempts = []
    if corridor:
        chosen = set(corridor)
        attempts.append(("Chosen regions", chosen))
        wider = set(chosen)
        for r in chosen:
            wider.update(region_adj[r])
        for r, nbs in region_adj.items():          # regions that lead INTO the corridor
            if chosen.intersection(nbs):
                wider.add(r)
        if wider != chosen:
            attempts.append(("Widened to neighbouring regions", wider))
    attempts.append(("Whole-map fallback", None))

    for mode, regions in attempts:
        allowed = None if regions is None else {
            n for r in regions for n in members[r]}
        path, cost, expanded = detailed_astar(road_map, start, goal, blocked, allowed)
        total_expanded += expanded
        if path is not None or regions is None:
            return {
                "found": path is not None,
                "path": path or [],
                "cost_m": cost,
                "nodes_expanded": total_expanded,
                "runtime_ms": (time.perf_counter() - t0) * 1000,
                "region_path": corridor,
                "mode": mode,
            }
