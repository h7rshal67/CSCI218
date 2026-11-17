"""Reproducible scaling experiments on the SAME algorithms used by the demo."""
from __future__ import annotations

import csv
import json
import platform
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flat_astar import flat_astar, route_cost
from two_tier_search import prepare_hierarchy, two_tier_search
from worlds import grid_world


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_benchmark(output=None, *, sizes=(32, 64, 128), seeds=10, repeats=10):
    rows = []
    for size in sizes:
        for seed in range(seeds):
            world = grid_world(size, seed)
            hierarchy = prepare_hierarchy(world)
            algorithms = {
                "Flat A*": lambda: flat_astar(world, world.start, world.goal,
                                             heuristic=world.heuristic(world.goal)),
                "Two-tier A*": lambda: two_tier_search(world, world.start, world.goal,
                                                       hierarchy=hierarchy),
            }
            for search in algorithms.values():
                search()
            for repeat in range(repeats):
                order = list(algorithms)
                if repeat % 2:
                    order.reverse()
                for method in order:
                    result = algorithms[method]()
                    assert result.found and result.path[0] == world.start and result.path[-1] == world.goal
                    assert abs(route_cost(world, result.path) - result.cost_m) < 1e-7
                    assert result.cost_m >= world.optimum
                    if method == "Flat A*":
                        assert result.cost_m == world.optimum
                    abstract = getattr(result, "abstract_expanded", 0)
                    rows.append({
                        "size": size, "seed": seed, "repeat": repeat, "method": method,
                        "runtime_ms": result.runtime_ms,
                        "detailed_nodes": result.nodes_expanded, "abstract_nodes": abstract,
                        "total_nodes": result.nodes_expanded + abstract,
                        "cost": result.cost_m,
                        "preprocessing_ms": hierarchy.preprocess_ms if method == "Two-tier A*" else 0,
                        "area_count": len(hierarchy.adj),
                    })
    summary = []
    for size in sizes:
        for method in ("Flat A*", "Two-tier A*"):
            group = [r for r in rows if r["size"] == size and r["method"] == method]
            record = {"size": size, "method": method}
            for metric in ("runtime_ms", "detailed_nodes", "abstract_nodes", "total_nodes",
                           "cost", "preprocessing_ms"):
                seed_means = [
                    statistics.mean(r[metric] for r in group if r["seed"] == seed)
                    for seed in range(seeds)
                ]
                record[metric + "_mean"] = statistics.mean(seed_means)
                record[metric + "_sd"] = statistics.stdev(seed_means) if seeds > 1 else 0.0
            summary.append(record)
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "platform": platform.platform(),
        "sizes": list(sizes), "seeds": list(range(seeds)), "repeats": repeats,
        "trial_count": len(rows), "region_rule": "8x8 tiles split into connected components",
        "timing": "Per-query time; map loading and region preprocessing reported separately.",
        "variability": "Sample standard deviation across per-map means.",
        "validation": "Every route checked; flat costs match independent BFS distances.",
    }
    if output:
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
        write_csv(output / "trials.csv", rows)
        write_csv(output / "summary.csv", summary)
        (output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return {"summary": summary, "metadata": metadata}


if __name__ == "__main__":
    data = run_benchmark(ROOT / "results" / "integrated")
    print(json.dumps(data, indent=2))
