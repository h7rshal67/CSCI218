import csv
import heapq
import random
import statistics
from collections import deque
from pathlib import Path
from time import perf_counter_ns

OUT = Path(__file__).resolve().parent


def grid(size, seed):
    rng = random.Random(seed)
    cells = {(r, c) for r in range(1, size - 1)
             for c in range(1, size - 1) if rng.random() >= .25}
    graph = {}
    for r, c in sorted(cells):
        graph[r, c] = tuple(p for p in ((r-1,c), (r+1,c), (r,c-1), (r,c+1)) if p in cells)
    start = min(graph, key=lambda p: (sum(p), p))
    distances = {start: 0}
    frontier = deque([start])
    while frontier:
        node = frontier.popleft()
        for nxt in graph[node]:
            if nxt not in distances:
                distances[nxt] = distances[node] + 1
                frontier.append(nxt)
    goal = max(distances, key=lambda p: (sum(p), p))
    return graph, start, goal, distances[goal]


def astar(graph, start, goal, allowed=None):
    def h(node):
        return abs(node[0] - goal[0]) + abs(node[1] - goal[1])

    queue = [(h(start), 0, start)]
    distance = {start: 0}
    parents = {}
    expanded = 0
    while queue:
        _, negative_cost, node = heapq.heappop(queue)
        cost = -negative_cost
        if cost != distance[node]:
            continue
        expanded += 1
        if node == goal:
            path = [goal]
            while path[-1] != start:
                path.append(parents[path[-1]])
            return path[::-1], expanded
        for nxt in graph[node]:
            if allowed is not None and nxt not in allowed:
                continue
            if cost + 1 < distance.get(nxt, float('inf')):
                distance[nxt] = cost + 1
                parents[nxt] = node
                heapq.heappush(queue, (cost + 1 + h(nxt), -cost - 1, nxt))
    return [], expanded


def region_graph(graph):
    areas = {node: (node[0] // 8, node[1] // 8) for node in graph}
    links = {area: set() for area in areas.values()}
    for node, neighbors in graph.items():
        for nxt in neighbors:
            if areas[node] != areas[nxt]:
                links[areas[node]].add(areas[nxt])
    return areas, links


def two_tier(graph, start, goal, areas, links):
    corridor, abstract = astar(links, areas[start], areas[goal])
    region_set = set(corridor)
    expanded = 0
    if region_set:
        for regions in (region_set, region_set.union(*(links[r] for r in region_set))):
            allowed = {node for node in areas if areas[node] in regions}
            path, work = astar(graph, start, goal, allowed)
            expanded += work
            if path:
                return path, expanded, abstract
    path, work = astar(graph, start, goal)
    return path, expanded + work, abstract


def run():
    rows = []
    for size in (32, 64, 128):
        for seed in range(10):
            graph, start, goal, optimum = grid(size, seed)
            before = perf_counter_ns()
            areas, links = region_graph(graph)
            prep_ms = (perf_counter_ns() - before) / 1e6
            queries = {
                'Flat A*': lambda: (*astar(graph, start, goal), 0),
                'Two-tier A*': lambda: two_tier(graph, start, goal, areas, links),
            }
            for query in queries.values():
                query()
            for repeat in range(10):
                order = list(queries)
                if repeat % 2:
                    order.reverse()
                for method in order:
                    before = perf_counter_ns()
                    path, expanded, abstract = queries[method]()
                    runtime_ms = (perf_counter_ns() - before) / 1e6
                    assert path[0] == start and path[-1] == goal
                    assert all(v in graph[u] for u, v in zip(path, path[1:]))
                    assert len(path) - 1 >= optimum
                    if method == 'Flat A*':
                        assert len(path) - 1 == optimum
                    rows.append(dict(size=size, seed=seed, repeat=repeat, method=method,
                                     runtime_ms=runtime_ms, nodes=expanded, regions=abstract,
                                     cost=len(path)-1, preprocessing_ms=prep_ms if abstract else 0))
    save('trials.csv', rows)
    summary = []
    for size in (32,64,128):
        for method in ('Flat A*', 'Two-tier A*'):
            group = [r for r in rows if r['size'] == size and r['method'] == method]
            record = dict(size=size, method=method)
            for key in ('runtime_ms','nodes','regions','cost','preprocessing_ms'):
                values = [statistics.mean(r[key] for r in group if r['seed'] == seed)
                          for seed in range(10)]
                record[key+'_mean'] = statistics.mean(values)
                record[key+'_sd'] = statistics.stdev(values)
            summary.append(record)
    save('summary.csv', summary)
    return summary


def save(name, rows):
    with (OUT / name).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


def plot(summary):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), layout='constrained')
    for ax, (metric, title) in zip(axes, [('nodes', 'Detailed nodes expanded'),
                                           ('runtime_ms', 'Query time (ms)'),
                                           ('cost', 'Route cost (moves)')]):
        for method, color, shift in [('Flat A*', '#23618c', -.07), ('Two-tier A*', '#b9552c', .07)]:
            group = [r for r in summary if r['method'] == method]
            ax.errorbar([i+shift for i in range(3)], [r[metric+'_mean'] for r in group],
                        yerr=[r[metric+'_sd'] for r in group], marker='o', capsize=3,
                        color=color, label=method)
        ax.set(xticks=range(3), xticklabels=['32 × 32', '64 × 64', '128 × 128'], title=title)
        ax.grid(axis='y', alpha=.25)
    axes[0].legend(frameon=False)
    fig.savefig(OUT / 'grid_benchmark.png', dpi=180)


if __name__ == '__main__':
    plot(run())
