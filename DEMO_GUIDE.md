# Demonstrating the project

Launch with the command:

    python demo.py

The browser loads the packaged Jumeirah map automatically. Keep the Python
terminal open during the demonstration.

1. **Normal road route.** Use Boxpark to Port de La Mer with no closure.
   Explain that flat A* searches the full network while two-tier selects
   areas and then searches inside them. Compare the routes, detailed
   expansions, abstract expansions, query time and preprocessing.
2. **Replay.** Click Replay search. The dots are real expansion events,
   not a simulated search order. The route appears when replay finishes.
   Use Fit route and the mouse wheel to examine it.
3. **Rerouting.** Select Block the shortest route. The same closed edges
   are supplied to both searches. Point out the magenta closure and
   the new route. For some origin/destination pairs a closure may make
   the goal unreachable; the program reports that result.
4. **No route and edge cases.** Select Close every exit at the start.
   Both methods must say No route. Then restore No closure and choose
   the same start and destination to demonstrate a zero-cost route.
5. **Scaling.** Switch to Obstacle grid. Compare 32x32, 64x64 and 128x128
   using a fixed seed. The black perimeter/obstacles cannot be traversed,
   each open cell belongs to a connected area, and moves are four-way.
6. **Repeated evidence.** Run the 600-search benchmark. It uses ten
   seeds and ten measured repeats at each of the three grid sizes.
   Show variability and download the raw CSVs. The outcome need not
   favor two-tier: explain the corridor, longer-route and overhead trade-offs.

The Original hub-route closure option reproduces the provided code's
60-m closure rule. It need not intersect the flat shortest path; an unchanged
flat cost is a valid outcome. Avoid presenting the older 7,346-m screenshot
as a measurement from this integrated program.

This is an offline distance-based simulation, not live navigation or a
validated humanitarian dispatch system.
