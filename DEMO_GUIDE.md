# Demonstrating the project

Run `python demo.py` or double-click `Start_Demo.bat`. Keep the terminal open.
The default browser page is the current Harshal interface.

## Suggested presentation sequence

1. **Normal road route.** Select Dubai road network, Boxpark, Port de La Mer
   and No closure. Run comparison. Identify the eight hubs and the blue flat
   route versus the dashed orange two-tier route. Explain that both algorithms
   receive the same directed network. A longer two-tier path is an observed
   trade-off, not an error to hide.
2. **Search effort.** Scroll to the results table. Compare detailed expansions,
   abstract expansions and their total, then query time and region preparation.
   Enable Regions and Explored nodes to show the base areas and real recorded
   detailed-node expansions. Repeated visits across attempts are counted even
   when their points overlap on the map.
3. **Rerouting.** With the same endpoints, choose Block the original shortest
   route and run again. Magenta marks closures supplied identically to both
   methods. Both returned routes must use open directed connections. For a
   fair before/after comparison, keep endpoints unchanged.
4. **Unreachable and zero-cost cases.** Select Isolate the start. Both methods
   should return No route. Restore No closure, then choose the same road hub
   for start and goal to show a zero-cost route. Restore different endpoints.
5. **Grid scaling.** Select Obstacle grid, No closure and seed 0. Run the 32×32,
   64×64 and 128×128 cases. Dark cells are obstacles. Routes use four-way moves;
   the displayed unit changes from metres to moves. Timings from a single
   interactive run can vary.
6. **Repeated evidence.** Open `results/integrated/RESULTS.md` and the final
   summary CSV. The full experiment covers three sizes, ten maps and ten
   measured repeats per method/map: 600 searches. Discuss mean query effort,
   route cost, variability and the separate region preparation overhead.

## Explain the implementation simply

- HTML supplies controls, the drawing area and the results table.
- JavaScript requests `/api/scene` to draw the map and `/api/run` to compare
  the searches. It displays measured values returned by Python.
- Python builds the shared world, applies closures, runs Tanisha's flat A*
  and the adapter using Faaiz's two-tier helpers, then validates the routes.
- Two-tier first selects regions, searches within them, widens the corridor
  if necessary and falls back to the full graph if needed.

The road-only hub-route scenario closes roads within 60 m of a hub-route
point. It may not intersect the flat shortest path. Older 7,213 m / 7,346 m
figures refer to earlier first-level route settings, not this demo's measured
flat/two-tier comparison. Use current live results for current claims.

Before presenting, run the automated suite and rehearse the scenarios above.
Use final integrated results consistently in slides/report; old charts may
describe a different implementation. This is an offline simulation, not live
navigation or a company dispatch deployment.
