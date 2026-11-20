"""Shared, offline map interface for the project algorithms and visual demo.

Road loading and road-based areas reuse Humna's unchanged osm_map.py.
Grid generation reuses Mia's supplied generator; rectangular grid tiles are
split into connected components to satisfy Topic 4's area specification.
"""
from __future__ import annotations

import math
import time
from collections import deque
from functools import lru_cache
from pathlib import Path

from flat_astar import flat_astar, haversine_m
from osm_map import RoadMap

ROOT = Path(__file__).resolve().parent


def connected_areas(adj, base_areas, blocked=()):
    """Split each original tile into connected open components (grid maps)."""
    closed = set(blocked)
    seen, areas, component = set(), {}, 0
    for start in adj:
        if start in seen:
            continue
        label = f"{base_areas[start]}.{component}"
        component += 1
        queue = deque([start])
        seen.add(start)
        while queue:
            node = queue.popleft()
            areas[node] = label
            for nb in adj[node]:
                if (node, nb) not in closed and nb not in seen and base_areas[nb] == base_areas[start]:
                    seen.add(nb)
                    queue.append(nb)
    return areas


class World:
    def __init__(self, kind, adj, coords, areas, *, size=0, seed=0,
                 start=None, goal=None, hubs=None, source=None, optimum=None):
        self.kind, self.adj, self.coords, self.area = kind, adj, coords, areas
        self.size, self.seed = size, seed
        self.start, self.goal = start, goal
        self.hubs = hubs or {}
        self.source = source
        self.optimum = optimum
        self.base_areas = {n: f"{n[0] // 8},{n[1] // 8}" for n in adj} if kind == "grid" else areas
        self.node_list = list(adj)
        self.indices = {n: i for i, n in enumerate(self.node_list)}
        self.load_ms = 0.0
        self._hub_map = None
        if kind == "road":
            lat_mid = sum(p[0] for p in coords.values()) / len(coords)
            lat_min = min(p[0] for p in coords.values())
            lon_min = min(p[1] for p in coords.values())
            scale = 111320 * math.cos(math.radians(lat_mid))
            self.positions = {n: ((p[1] - lon_min) * scale, (p[0] - lat_min) * 111320)
                              for n, p in coords.items()}
        else:
            self.positions = {n: (n[1] + .5, size - n[0] - .5) for n in adj}

    def distance(self, a, b):
        if self.kind == "road":
            return haversine_m(a, b)
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def heuristic(self, goal):
        return lambda node: self.distance(self.coords[node], self.coords[goal])

    def endpoints(self, start_name=None, goal_name=None):
        if self.kind == "grid":
            return self.start, self.goal
        if start_name not in self.hubs or goal_name not in self.hubs:
            raise ValueError("Choose a start and destination from the map's hubs.")
        return self.hubs[start_name], self.hubs[goal_name]

    def scene(self):
        labels = sorted(set(self.area.values()))
        label_index = {a: i for i, a in enumerate(labels)}
        edges = set()
        for u, neighbors in self.adj.items():
            for v in neighbors:
                a, b = self.indices[u], self.indices[v]
                edges.add((min(a, b), max(a, b)))
        nodes = [[*self.positions[n], label_index[self.area[n]]] for n in self.node_list]
        return {
            "kind": self.kind, "size": self.size, "seed": self.seed,
            "nodes": nodes, "edges": sorted(edges), "region_labels": labels,
            "hubs": [{"name": name, "node": self.indices[n]} for name, n in self.hubs.items()],
            "node_count": len(self.adj),
            "directed_edge_count": sum(map(len, self.adj.values())),
            "load_ms": self.load_ms,
            "start": self.indices[self.start] if self.start is not None else None,
            "goal": self.indices[self.goal] if self.goal is not None else None,
            "unit": "m" if self.kind == "road" else "moves",
        }


@lru_cache(maxsize=1)
def road_world():
    before = time.perf_counter()
    rm = RoadMap(str(ROOT / "data" / "jumeirah.osm"))
    world = World("road", rm.adj, rm.coords, rm.area, hubs=rm.hub_node, source=rm)
    world.load_ms = (time.perf_counter() - before) * 1000
    return world


def grid_world(size=32, seed=0):
    from experiments.mia_original_benchmark import grid
    if size not in (32, 64, 128):
        raise ValueError("Grid size must be 32, 64 or 128.")
    if not 0 <= seed <= 9999:
        raise ValueError("Seed must be between 0 and 9999.")
    before = time.perf_counter()
    graph, start, goal, optimum = grid(size, seed)
    adj = {u: {v: 1.0 for v in vs} for u, vs in graph.items()}
    coords = {u: u for u in adj}
    tiles = {u: f"{u[0] // 8},{u[1] // 8}" for u in adj}
    world = World("grid", adj, coords, connected_areas(adj, tiles),
                  size=size, seed=seed, start=start, goal=goal, optimum=optimum)
    world.load_ms = (time.perf_counter() - before) * 1000
    return world


@lru_cache(maxsize=12)
def get_world(kind="road", size=32, seed=0):
    if kind == "road":
        return road_world()
    if kind == "grid":
        return grid_world(size, seed)
    raise ValueError("Unknown map type.")


def closures_for(world, start, goal, scenario):
    """Construct one closure set that is passed unchanged to both algorithms."""
    if scenario == "none":
        return set(), "No road closures."
    if scenario == "isolate":
        return {(start, v) for v in world.adj[start]}, "All outgoing edges at the start are closed."
    if scenario == "hub":
        if world.kind != "road":
            raise ValueError("The hub-route closure is a road-map scenario.")
        from first_level_search import build_hub_map, first_level_search
        if world._hub_map is None:
            world._hub_map = build_hub_map(world.source)
        start_name = next(h for h, n in world.hubs.items() if n == start)
        goal_name = next(h for h, n in world.hubs.items() if n == goal)
        macro = first_level_search(world.source, world._hub_map, start_name, goal_name)
        if not macro["legs"]:
            return set(), "The selected start and destination coincide; no hub-route closure was created."
        leg = macro["legs"][len(macro["legs"]) // 2]
        point = leg[len(leg) // 2]
        return world.source.edges_near(*world.coords[point], 60), (
            "60 m closure around the middle of the original hub route; "
            "this may leave the flat shortest route unchanged."
        )
    if scenario != "targeted":
        raise ValueError("Unknown closure scenario.")
    baseline = flat_astar(world, start, goal, heuristic=world.heuristic(goal))
    if len(baseline.path) < 3:
        return set(), "No internal route point is available for a closure."
    if world.kind == "road":
        # Select a reproducible on-route closure with a viable detour when
        # possible. A separate scenario demonstrates an unreachable goal.
        for fraction in (.35, .65, .2, .8, .5):
            mid = baseline.path[int((len(baseline.path) - 1) * fraction)]
            closed = world.source.edges_near(*world.coords[mid], 60)
            detour = flat_astar(world, start, goal, closed, heuristic=world.heuristic(goal))
            if detour.found and detour.cost_m > baseline.cost_m + 1e-6:
                return closed, "60 m closure on the original shortest route, selected to demonstrate a feasible detour."
        mid = baseline.path[len(baseline.path) // 2]
        return world.source.edges_near(*world.coords[mid], 60), (
            "60 m closure on the original shortest route; a detour may be unavailable."
        )
    mid = baseline.path[len(baseline.path) // 2]
    closed = {(mid, v) for v in world.adj[mid]}
    closed |= {(u, mid) for u in world.adj if mid in world.adj[u]}
    return closed, "The midpoint cell of the original shortest route is closed."
