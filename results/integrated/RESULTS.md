# Final integrated grid experiment

These results were regenerated from the current integrated code on 2026-11-20T16:19:23.000050+00:00.

Protocol: 32×32, 64×64 and 128×128 grids; seeds 0–9; one warm-up per method/map; ten measured repeats per method/map. The 600 measured searches use alternating method order. Every returned route was checked, and flat costs matched independent BFS distances.

Values below are means ± sample standard deviations across the ten per-map means. Query time excludes shared map loading and region preparation. Preprocessing is prepared once per map and reused for its queries.

## Runtime and preparation

| Grid | Flat query (ms) | Two-tier query (ms) | Two-tier preparation (ms) |
| --- | --- | --- | --- |
| 32×32 | 0.675 ± 0.381 | 0.411 ± 0.227 | 0.871 ± 0.217 |
| 64×64 | 2.991 ± 2.156 | 1.093 ± 0.764 | 3.928 ± 0.838 |
| 128×128 | 8.615 ± 6.178 | 2.291 ± 1.549 | 15.553 ± 1.863 |

## Expansions and path cost

Total expansions include detailed and abstract work; all widening/fallback attempts are counted.

| Grid | Flat total expansions | Two-tier total expansions | Flat cost (moves) | Two-tier cost (moves) |
| --- | --- | --- | --- | --- |
| 32×32 | 288.1 ± 159.8 | 151.5 ± 82.1 | 47.3 ± 22.9 | 47.7 ± 23.2 |
| 64×64 | 1069.1 ± 778.1 | 376.4 ± 259.2 | 85.8 ± 57.0 | 89.4 ± 59.5 |
| 128×128 | 3320.9 ± 2384.5 | 803.9 ± 566.7 | 174.3 ± 119.4 | 180.1 ± 123.4 |

## Interpretation and limits

- In this run, two-tier had lower mean query times and fewer mean total expansions at all three grid sizes, with higher mean path costs.
- Region preparation has an initial cost. For a single query, preparation plus query time can exceed flat query time; repeated queries can reuse preparation.
- These are observations on this map sample and machine, not a guarantee for every graph or query. Standard deviation reflects variation between maps.
- The interactive road case can show a longer and more expensive two-tier search. Do not describe grid averages as proof that every road query improves.
- The interactive view collects expansion traces; the benchmark disables trace collection to measure search queries. Both use the same algorithm implementations.
- Update report figures/tables using these files rather than mixing measurements from earlier teammate versions.

Files: `trials.csv` contains all raw trials; `summary.csv` contains all metric summaries; `metadata.json` records the environment/protocol; `source_hashes.json` records the source snapshot.

Environment: Python 3.14.7; Windows-11-10.0.26200-SP0.
