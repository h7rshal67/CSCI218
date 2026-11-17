# CSCI218 – Multi-Layered Search

CSCI218 Foundations of Artificial Intelligence  
Group Project: Topic 4 / Project H

## Project overview

This project compares two-tier pathfinding with flat A* search.

The objective is to investigate how searching an abstract map of
areas first can reduce the work needed to find a detailed route.

## Planned approaches

### Flat A*
Searches the detailed map directly from the start to the goal.

### Two-tier search
First finds a route through abstract areas, then uses that route
to guide searches in the detailed map.

The implementation must handle valid maps beyond a single
demonstration example.

## Planned evaluation

Both approaches will be tested on the same maps of increasing size.

The comparison will measure:
- Nodes expanded
- Runtime
- Path cost

Experiments will use reproducible configurations and fixed random
seeds where randomness is involved. Results will include repeated
runs and summary statistics.

## Team responsibilities

| Member | Main responsibility | Report sections |
| --- | --- | --- |
| Humna | Maps, regions and disruption scenarios | Motivation; Conclusion |
| Tanisha | Flat A* and edge-case tests | Technical Requirements; Limitations |
| Faaiz | Two-tier search | Main Constructs; References |
| Mia | Experiments, results and charts | Executive Summary; Results |
| Harshal | Visual demo and README | Implementation; Appendices |

## Installation and running

Installation instructions, dependencies and exact commands will
be added when the team's code is integrated and verified.

## Collaboration

- Use a separate branch for each module.
- Have a teammate review changes before merging into main.
- Commit your own contributions under your own identity.
- Use clear commit messages describing each change.

## Current status

Repository setup is in progress.
Implementation files, verified run instructions and experimental
results will be added as the team integrates its work.
