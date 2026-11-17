# Source and integration notes

| Source | Preserved work | Integration changes |
| --- | --- | --- |
| Humna, supplied inside Tanisha's ZIP | osm_map.py, first_level_search.py and data/jumeirah.osm | Map loader and hub search copied unchanged. Hub search is used only to reproduce the original hub-route closure. |
| Tanisha, corrected complete ZIP | Full-road-network flat A*, original algorithm snapshot and baseline tests | Added optional map-specific heuristic, allowed-node corridor and real expansion trace. Updated real-map test data path for this layout. |
| Faaiz, FAIZ Part.ipynb | Original notebook in team_sources | Adapted corridor selection, one-ring widening and whole-map fallback to the shared map interface. Removed online OSMnx loading and K-Means dependency from the integrated execution path. |
| Mia, MIA CSCI218.zip | Original benchmark and CSVs | Reused deterministic grid generation. Added an integrated benchmark that imports the actual demo algorithms; grid regions are split into connected components. |
| Demo integration prepared in this session for Harshal's review | demo.py, worlds.py, two_tier_search.py, web/, integration tests and running instructions | Local visual demo, closure controls, replay and repeatable shared-map experiments. These are integration edits, not untouched teammate submissions. |

## Behavioral differences from the original notebook

- Both algorithms use the identical directed adjacency map, endpoints, edge
  lengths and directed closure set.
- An abstract edge exists only where an open directed road/cell edge crosses
  between areas. Center-to-center distances guide abstract corridor selection;
  they are surrogate weights, not the final road-route length.
- The abstract heuristic targets the destination area's center. Detailed A*
  uses haversine distance for roads and Manhattan distance for grids.
- Grid tiles are split into connected open components, including after a
  closure. Eight-by-eight tiles may therefore create more than one area.
- Corridor widening includes neighbouring areas. If restricted searches fail,
  a whole-map fallback preserves reachability. Every detailed attempt is
  counted. Abstract expansions and region preparation are reported separately.
- Faaiz's independently downloaded graph and its old distances are not used.
  The integrated road case uses the packaged map with 23,400 nodes.

## Metrics and boundaries

An expansion is a non-stale priority-queue removal, including the destination.
Start equals goal returns a zero-cost path with zero expansions. Repeat
expansions across widening/fallback attempts are included.

Query timing includes region selection, construction of the permitted-node
set and all detailed attempts. Region-graph preprocessing and common map
loading are outside query timing and displayed separately. Independent
Dijkstra/path validation and construction of the closure scenario are also
outside query timing.

The benchmark reports mean values across ten maps and sample standard
deviation of the ten per-map means, after ten measured repeats on each map.

## Data and contribution records

Road data is © OpenStreetMap contributors, available under the Open Database
License (ODbL): https://opendatacommons.org/licenses/odbl/1-0/
Attribution: https://www.openstreetmap.org/copyright
The extract was supplied by the team; its original extraction date was not
provided. Do not invent one.

Original report drafts have not been changed. The old images and benchmark
outputs describe their original code/settings; they are not live-demo results.
Keep actual Git commit evidence and acknowledge the assistant's involvement
according to the assessment rules. Teammates should review their imported
and adapted components, and record their own subsequent contributions.
