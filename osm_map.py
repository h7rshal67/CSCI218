"""
osm_map.py  -  Step 1: turn the OpenStreetMap (.osm) file into a road graph,
pick the hubs, and split the map into one area per hub.

Used by first_level_search.py (the big-picture search).
Only the Python standard library is needed.

Map data: (c) OpenStreetMap contributors, available under the Open Database
License (ODbL) - https://www.openstreetmap.org/copyright
"""
import math
import heapq
import warnings
import xml.etree.ElementTree as ET

# Road types a car can drive on (footways, paths, crossings etc. are ignored)
DRIVABLE = {"motorway", "trunk", "primary", "primary_link", "secondary",
            "secondary_link", "tertiary", "tertiary_link", "residential",
            "unclassified", "living_street", "service"}

# Hubs = the "hotspots" of the map. Name -> OSM name to look up (or lat/lon).
# Coordinates were read from the .osm file (named shops, clinics, harbour...).
# Hubs whose name is not found in the downloaded map are skipped with a warning, so you
# can freely edit this list: use ("name", "<name exactly as on openstreetmap.org>")
# or ("latlon", lat, lon).
HUBS = {
    "Boxpark":              ("name", "Boxpark"),
    "Art House":            ("name", "Art House Dubai"),
    "Fishing Harbour":      ("name", "Jumeirah Fishing Harbour"),
    "Carrefour Market":     ("name", "Carrefour Market"),
    # "Mercato Shopping Mall" appears three times in the OSM file, two at (25.2156, 55.2510)
    # and one at (25.2163, 55.2533). The third is the mall itself, so it is pinned here
    # instead of letting the lookup pick one silently.
    "Mercato Mall":         ("latlon", 25.2162583, 55.2532819),
    "Jumeirah Beach Centre": ("name", "Jumeriah Beach Cental Center"),   # spelled as in OSM
    "La Mer":               ("name", "La Mer"),
    "Port de La Mer":       ("name", "Port de La Mer"),
}


def haversine_m(lat1, lon1, lat2, lon2):
    """Straight-line distance in metres between two lat/lon points."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class RoadMap:
    """Holds the road graph, the hubs and the area of every road node."""

    def __init__(self, osm_path):
        self.coords = {}          # node id -> (lat, lon)
        self.adj = {}             # node id -> {neighbour id: metres}
        self.hub_node = {}        # hub name -> road node id it is snapped to
        self.hub_pos = {}         # hub name -> (lat, lon) of the real place
        self.hub_snap_m = {}      # hub name -> metres from the real place to its road node
        self.ambiguous_names = set()   # OSM names that appear at places > 20 m apart
        self.area = {}            # node id -> hub name (the area it belongs to)
        self._load(osm_path)
        self._keep_largest_connected_part()
        self._place_hubs()
        self._make_areas()

    # ---------- reading the file ----------
    def _load(self, osm_path):
        root = ET.parse(osm_path).getroot()
        all_nodes = {}
        named = {}                                   # name -> (lat, lon), first one wins

        def remember(name, pos):
            """Keep the FIRST place with this name; note names that occur in several places."""
            if name not in named:
                named[name] = pos
            elif haversine_m(*named[name], *pos) > 20:
                self.ambiguous_names.add(name)

        for n in root.iter("node"):
            pos = (float(n.get("lat")), float(n.get("lon")))
            all_nodes[n.get("id")] = pos
            for t in n.findall("tag"):
                if t.get("k") in ("name", "name:en"):
                    remember(t.get("v"), pos)
        for w in root.iter("way"):
            tags = {t.get("k"): t.get("v") for t in w.findall("tag")}
            refs = [nd.get("ref") for nd in w.findall("nd")]
            for key in ("name", "name:en"):
                if key in tags and refs:
                    lats = [all_nodes[r][0] for r in refs if r in all_nodes]
                    lons = [all_nodes[r][1] for r in refs if r in all_nodes]
                    if lats and tags.get("highway") not in DRIVABLE:   # roads are not hubs
                        remember(tags[key], (sum(lats) / len(lats), sum(lons) / len(lons)))
            if tags.get("highway") not in DRIVABLE:
                continue
            oneway = tags.get("oneway") in ("yes", "true", "1") or tags.get("junction") == "roundabout"
            reverse = tags.get("oneway") == "-1"
            for a, b in zip(refs, refs[1:]):
                if a not in all_nodes or b not in all_nodes:
                    continue
                d = haversine_m(*all_nodes[a], *all_nodes[b])
                self.coords[a] = all_nodes[a]
                self.coords[b] = all_nodes[b]
                if reverse:
                    a, b = b, a
                self.adj.setdefault(a, {})[b] = d
                self.adj.setdefault(b, {})
                if not oneway and not reverse:
                    self.adj[b][a] = d
                elif reverse:
                    pass
        self._named = named

    def _keep_largest_connected_part(self):
        """Keep only roads that can all reach each other (strongly connected)."""
        # Kosaraju, written without recursion
        order, seen = [], set()
        for s in self.adj:
            if s in seen:
                continue
            stack = [(s, iter(self.adj[s]))]
            seen.add(s)
            while stack:
                node, it = stack[-1]
                for nb in it:
                    if nb not in seen:
                        seen.add(nb)
                        stack.append((nb, iter(self.adj[nb])))
                        break
                else:
                    order.append(node)
                    stack.pop()
        rev = {}
        for u, nbrs in self.adj.items():
            rev.setdefault(u, [])
            for v in nbrs:
                rev.setdefault(v, []).append(u)
        comp_of, comps = {}, []
        for s in reversed(order):
            if s in comp_of:
                continue
            comp, stack = [], [s]
            comp_of[s] = len(comps)
            while stack:
                u = stack.pop()
                comp.append(u)
                for v in rev[u]:
                    if v not in comp_of:
                        comp_of[v] = len(comps)
                        stack.append(v)
            comps.append(comp)
        keep = set(max(comps, key=len))
        self.adj = {u: {v: d for v, d in nbrs.items() if v in keep}
                    for u, nbrs in self.adj.items() if u in keep}
        self.coords = {u: self.coords[u] for u in self.adj}

    # ---------- hubs and areas ----------
    def nearest_node(self, lat, lon):
        return min(self.coords, key=lambda n: haversine_m(lat, lon, *self.coords[n]))

    def _place_hubs(self):
        for name, spec in HUBS.items():
            if spec[0] == "name":
                if spec[1] not in self._named:
                    print(f"  (warning) hub '{name}': '{spec[1]}' is not in this map - skipped")
                    continue
                if spec[1] in self.ambiguous_names:
                    warnings.warn(f"hub '{name}': the name '{spec[1]}' occurs at several places in the "
                                  f"map; the first one is used. Pin it with ('latlon', lat, lon).")
                lat, lon = self._named[spec[1]]
            else:
                lat, lon = spec[1], spec[2]
            self.hub_pos[name] = (lat, lon)
            self.hub_node[name] = self.nearest_node(lat, lon)
            self.hub_snap_m[name] = haversine_m(lat, lon, *self.coords[self.hub_node[name]])
        if len(self.hub_node) < 2:
            raise ValueError("Fewer than 2 hubs found - edit HUBS in osm_map.py for your map")
        # two hubs on the same road node would silently lose one area in _make_areas
        owner = {}
        for name, node in self.hub_node.items():
            if node in owner:
                raise ValueError(f"hubs '{owner[node]}' and '{name}' snap to the same road node; "
                                 f"move one of them in HUBS")
            owner[node] = name

    def _make_areas(self):
        """Every road node belongs to the hub it is closest to BY ROAD (not straight line),
        found by running Dijkstra from all hubs at once. This keeps each area in one
        connected piece that contains its hub."""
        dist, heap = {}, []
        for h, n in self.hub_node.items():
            dist[n] = 0.0
            self.area[n] = h
            heap.append((0.0, n))
        heapq.heapify(heap)
        while heap:
            d, u = heapq.heappop(heap)
            if d > dist[u]:
                continue
            for v, w in self.adj[u].items():
                if d + w < dist.get(v, float("inf")):
                    dist[v] = d + w
                    self.area[v] = self.area[u]
                    heapq.heappush(heap, (d + w, v))

    # ---------- roadblocks ----------
    def edges_near(self, lat, lon, radius_m):
        """All road edges with an end within radius_m of a point.
        Use this to build a fake roadblock scenario (pass the result as `blocked`)."""
        blocked = set()
        for u, nbrs in self.adj.items():
            for v in nbrs:
                if (haversine_m(lat, lon, *self.coords[u]) <= radius_m or
                        haversine_m(lat, lon, *self.coords[v]) <= radius_m):
                    blocked.add((u, v))
        return blocked


def dijkstra_path(adj, source, target, allowed=None, blocked=frozenset()):
    """Shortest road route source -> target. Returns (metres, [node ids]) or (None, None).
    allowed: optional set of nodes the route may use. blocked: set of closed (u, v) edges."""
    dist, prev, heap = {source: 0.0}, {}, [(0.0, source)]
    while heap:
        d, u = heapq.heappop(heap)
        if u == target:
            path = [u]
            while u in prev:
                u = prev[u]
                path.append(u)
            return d, path[::-1]
        if d > dist.get(u, float("inf")):
            continue
        for v, w in adj[u].items():
            if (allowed is not None and v not in allowed) or (u, v) in blocked:
                continue
            nd = d + w
            if nd < dist.get(v, float("inf")):
                dist[v], prev[v] = nd, u
                heapq.heappush(heap, (nd, v))
    return None, None
