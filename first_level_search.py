"""
first_level_search.py  -  Step 2: the FIRST-LEVEL (big-picture) search.

Idea
----
The map is split into areas, one per hub. Instead of searching every road node,
we first search a tiny "hub map":
    * each hub is one point,
    * two hubs are joined if their areas touch,
    * the cost of a join is the real road distance between the two hubs.
A* then finds the best chain of hubs (the "macro path") from start to goal.

A* gives every hub a score:  score = distance travelled so far
                                    + straight-line distance still to go (the guess)
and always expands the lowest score next, so it skips hubs that lead the wrong way.

The result also keeps the road route between each pair of hubs, so the
second-level (detailed) search can work inside the chosen areas only.
"""
import heapq
import time
from osm_map import RoadMap, dijkstra_path, haversine_m


def build_hub_map(road_map, blocked=frozenset()):
    """Build the abstract (hub-level) graph.
    Returns {hub: {neighbour hub: (metres, [road node ids])}}.
    `blocked` = set of closed road edges (u, v); closed roads are never used."""
    # which areas touch? (a road edge that goes from one area into another)
    touching = set()
    for u, nbrs in road_map.adj.items():
        for v in nbrs:
            if (u, v) in blocked:
                continue
            a, b = road_map.area[u], road_map.area[v]
            if a != b:
                touching.add((a, b))
                touching.add((b, a))      # areas that touch can be driven both ways
    hub_map = {h: {} for h in road_map.hub_node}
    for a, b in touching:
        # real shortest road route between the two hubs (closed roads are skipped)
        metres, path = dijkstra_path(road_map.adj, road_map.hub_node[a],
                                     road_map.hub_node[b], None, blocked)
        if metres is not None:
            hub_map[a][b] = (metres, path)
    return hub_map


def first_level_search(road_map, hub_map, start, goal, use_heuristic=True):
    """A* over the hub map.
    use_heuristic=False turns the guess off (plain Dijkstra) - handy for comparing.
    Returns a dict with the macro path and the numbers needed for the report."""
    t0 = time.perf_counter()
    for name in (start, goal):
        if name not in road_map.hub_node:
            raise ValueError(f"unknown hub '{name}'. Hubs: {', '.join(sorted(road_map.hub_node))}")

    def guess(h):
        """Straight-line distance between the two hubs' ROAD nodes. A road route between those
        nodes can never be shorter, so the guess never overestimates (A* stays optimal).
        Using the real place positions instead could overestimate by a few metres, because a
        hub's road node can be up to ~150 m away from the place itself."""
        if not use_heuristic:
            return 0.0
        return haversine_m(*road_map.coords[road_map.hub_node[h]],
                           *road_map.coords[road_map.hub_node[goal]])

    g = {start: 0.0}
    came = {}
    heap = [(guess(start), start)]
    closed = set()
    expanded = 0
    while heap:
        _, h = heapq.heappop(heap)
        if h in closed:
            continue
        closed.add(h)
        expanded += 1
        if h == goal:
            hubs = [h]
            while h in came:
                h = came[h]
                hubs.append(h)
            hubs.reverse()
            legs = [hub_map[a][b][1] for a, b in zip(hubs, hubs[1:])]
            return {"found": True, "macro_path": hubs, "cost_m": g[goal],
                    "nodes_expanded": expanded, "legs": legs,
                    "runtime_ms": (time.perf_counter() - t0) * 1000}
        for nb, (metres, _) in hub_map[h].items():
            if g[h] + metres < g.get(nb, float("inf")):
                g[nb] = g[h] + metres
                came[nb] = h
                heapq.heappush(heap, (g[nb] + guess(nb), nb))
    return {"found": False, "macro_path": [], "cost_m": None, "nodes_expanded": expanded,
            "legs": [], "runtime_ms": (time.perf_counter() - t0) * 1000}
