# CSCI218 – Multi-Layered Search

CSCI218 Foundations of Artificial Intelligence · Topic 4 / Project H

This project compares flat A* with two-tier search on the same directed graph.
It includes a local browser demo, an OpenStreetMap road case, generated obstacle
grids, closure scenarios, automated tests and repeated scaling experiments.

## Run the demo

Requires Python 3.10 or later and a modern browser. No external Python packages,
API keys or internet map downloads are needed.

From this repository's folder:

```powershell
python demo.py
```

On Windows, you can also double-click `Start_Demo.bat`. The browser opens the
current Harshal demo at http://127.0.0.1:8765. Keep the terminal open while using
the page; press Ctrl+C there to stop the server.

If the port is occupied, use `python demo.py --port 8766`. For a browser opened
manually, use `http://127.0.0.1:8766/harshal.html`. Open the page through the
Python server so it can request map and search data.

## Use the controls

- **Dubai road network:** choose any of the eight named start/destination hubs.
- **Obstacle grid:** choose 32×32, 64×64 or 128×128 and a seed from 0–9999.
  The same size and seed reproduce the same map and endpoints.
- **No closure:** compare the two routes on the original graph.
- **Block the original shortest route:** close connections on a baseline route.
  The road scenario searches for a feasible detour where possible.
- **Close roads near the hub route:** road-only, 60 m closure around a point on
  the first-level hub route. This may leave the flat shortest route unchanged.
- **Isolate the start:** close its outgoing connections to demonstrate no route.
- **Regions / Explored nodes:** show the base partition and actual detailed-node
  expansion traces. The coloured traces are an overlay, not an animation.

Click **Run comparison** after changing the endpoints or closure scenario.
Blue is flat A*, dashed orange is two-tier and magenta marks closed connections.
Road distances are metres; grid costs are four-way moves. Both searches receive
identical graph data, endpoints, weights and directed closures.

## Algorithms and measurements

Flat A* searches the full detailed graph. Two-tier first searches an abstract
region graph, then searches the detailed graph inside the selected corridor.
It widens the corridor and ultimately uses the full graph if a restricted
search cannot find a route. Its route can be longer than the flat optimum.

The table reports distance, detailed and abstract expansions, total expansions,
query time, region preparation and detailed search attempts. Repeated detailed
work across attempts is included. Query time includes abstract search, corridor
filtering and detailed attempts. Map loading and region preparation are outside
query time. Scenario construction and independent validation are also outside it.

Every returned route is checked against open directed edges. The interactive
flat baseline is independently checked against Dijkstra. A zero-length route
is valid when the start and goal coincide. No-route results remain visible.

## Tests and repeated experiments

Run the Python tests:

```powershell
python -m unittest discover -s tests -v
```

The current integrated suite contains 48 tests. The road, closure, grid and
isolated-start views have also been checked in the browser.

Run the full benchmark:

```powershell
python -m experiments.integrated_benchmark
```

It imports the same search implementations as the demo and runs 32×32, 64×64
and 128×128 grids, ten seeds and ten measured repeats per method/map: **600
measured searches**, plus one warm-up per method/map. Execution order alternates.
Grid regions use 8×8 tiles split into connected components.

Outputs are `results/integrated/trials.csv`, `summary.csv` and `metadata.json`.
Every route is validated and flat costs are checked against independent BFS
distances. Summary standard deviations are across the ten per-map means.
`results/integrated/RESULTS.md` describes the packaged final run. Timings depend
on the machine and workload; rerunning the benchmark will change runtime values.

## Main files

| File | Purpose |
| --- | --- |
| `demo.py` | Local server, shared search API and route validation |
| `web/harshal.html` | Current demo controls, canvas and results table |
| `web/harshal.css` | Current demo styling |
| `web/harshal.js` | API requests, map/route drawing and result display |
| `osm_map.py`, `first_level_search.py` | Humna's corrected map and hub-search code |
| `flat_astar.py` | Tanisha's updated flat baseline with compatibility extensions |
| `faaiz_two_tier_search.py` | Faaiz's corrected region and detailed search helpers |
| `two_tier_search.py` | Shared road/grid adapter calling Faaiz's helpers |
| `worlds.py` | Shared worlds, grid partitions and closure construction |
| `experiments/integrated_benchmark.py` | Repeated evaluation of the integrated code |
| `experiments/mia_original_benchmark.py` | Preserved benchmark source and reused grid generator |
| `tests/` | Algorithm and integration checks |

Earlier reference interface files are preserved in `web/`; the default page
is `harshal.html`. See `DEMO_GUIDE.md` for the presentation sequence and
`SOURCE_NOTES.md` for integration and attribution details.

## Team responsibilities

| Member | Main responsibility | Report sections |
| --- | --- | --- |
| Humna | Maps, regions and disruption scenarios | Motivation; Conclusion |
| Tanisha | Flat A* and edge-case tests | Technical Requirements; Limitations |
| Faaiz | Two-tier search | Main Constructs; References |
| Mia | Experiments, results and charts | Executive Summary; Results |
| Harshal | Visual demo and README | Implementation; Appendices |

Commit actual contributions under each member's own identity, use clear
messages, and review branch changes before merging into `main`. Earlier
teammate reports/outputs describe their original code versions; use the final
integrated measurements when discussing this demo.

## Data source

The road case uses the team-supplied `data/jumeirah.osm` extract, with 23,400
nodes and 35,081 directed connections in the current loader. Road data is
© OpenStreetMap contributors, licensed under the Open Database License:
https://opendatacommons.org/licenses/odbl/1-0/.
Attribution: https://www.openstreetmap.org/copyright.

Grids are synthetic maps generated by project code; closures are simulated.
This is an offline, distance-based educational demonstration.
