# CSCI218 – Multi-Layered Search

CSCI218 Foundations of Artificial Intelligence  
Group Project: Topic 4 / Project H

## Project overview

This project compares two-tier pathfinding with flat A* search.

The offline demo shows both methods on identical directed graphs, with
route drawing, real expansion replay, closure scenarios and repeatable
grid experiments. The road case uses the team's packaged Jumeirah OSM
snapshot. Grids of increasing size retain the core Topic 4 evaluation.

## Algorithms

### Flat A*
Searches the detailed map directly from the start to the goal.

### Two-tier search
First finds a route through abstract areas, then uses that route
to guide searches in the detailed map.

The implementation must handle valid maps beyond a single
demonstration example.

## Reproducible evaluation

Both approaches are tested on the same maps of increasing size.

The comparison will measure:
- Nodes expanded
- Runtime
- Path cost

The integrated benchmark uses 32x32, 64x64 and 128x128 grids, seeds 0-9,
one warm-up and ten measured repeats per method/map: 600 measured searches.
Grid regions are 8x8 tiles split into connected components. Outputs include
raw trials, means, sample standard deviations across per-map means and
environment metadata.

Query time includes the abstract query, corridor filtering and every
detailed attempt. Common map loading and region-graph preprocessing are
excluded and reported separately. Validation runs outside query timing.
The two-tier method is approximate: it may return a longer route and may
be slower. Results are displayed without assuming which method wins.

## Team responsibilities

| Member | Main responsibility | Report sections |
| --- | --- | --- |
| Humna | Maps, regions and disruption scenarios | Motivation; Conclusion |
| Tanisha | Flat A* and edge-case tests | Technical Requirements; Limitations |
| Faaiz | Two-tier search | Main Constructs; References |
| Mia | Experiments, results and charts | Executive Summary; Results |
| Harshal | Visual demo and README | Implementation; Appendices |

## Installation and running

Requires Python 3.10 or later and a modern browser. There are no external
Python packages, API keys or online map downloads.

From the project folder:

    python demo.py

On Windows you can also double-click Start_Demo.bat. Keep the Python
terminal open while using the demo. Press Ctrl+C there to stop it.
If the browser does not open, visit http://127.0.0.1:8765.
If that port is occupied, run:

    python demo.py --port 0

The terminal prints the chosen local URL.

Run the tests:

    python -m unittest discover -s tests -v

Run the full benchmark independently:

    python -m experiments.integrated_benchmark

The browser's Run 600-search benchmark button uses the same runner.
Results are written to results/integrated/trials.csv, summary.csv and
metadata.json. Download links appear after a browser benchmark completes.

## Demonstration controls

- Switch between Dubai roads and obstacle grids.
- Choose road start/destination hubs, or grid size and deterministic seed.
- Compare no closure, an on-route closure, the original 60-m hub-route
  closure, and a deliberately unreachable destination.
- Use Replay search, region/exploration toggles, Fit map, Fit route and
  mouse zoom/pan.
- A route is checked against the open directed edges. Flat A* is also
  checked against an independent Dijkstra search.

See DEMO_GUIDE.md for a short rehearsal sequence.

## Files and attribution

| File | Purpose |
| --- | --- |
| demo.py | Local server, controls API and independent route validation |
| flat_astar.py | Tanisha baseline with documented integration extensions |
| two_tier_search.py | Adapted Faaiz corridor/widening/fallback strategy |
| osm_map.py and first_level_search.py | Humna's unchanged supporting code |
| worlds.py | Shared road/grid interface, connected grid areas and closures |
| web/ | Browser interface and canvas drawing |
| experiments/integrated_benchmark.py | Benchmarks the actual integrated algorithms |
| experiments/mia_original_benchmark.py | Preserved Mia script; grid generator reused |
| team_sources/ | Original Faaiz notebook and Tanisha baseline snapshot |
| tests/ | Baseline and shared-map integration verification |

SOURCE_NOTES.md documents source ownership, adaptation and metric boundaries.
The supplied reports have not been edited.

Road data is © OpenStreetMap contributors, licensed under the Open Database
License: https://opendatacommons.org/licenses/odbl/1-0/
Attribution: https://www.openstreetmap.org/copyright
This is a static distance-based educational simulation.

## Collaboration

- Use a separate branch for each module.
- Have a teammate review changes before merging into main.
- Commit your own contributions under your own identity.
- Use clear commit messages describing each change.

## Current status

Working offline demo and shared-map integration, ready for team review.
24 automated baseline/integration tests pass.
Original teammate outputs are preserved separately from integrated results.
