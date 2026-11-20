"""Launch the local, offline CSCI218 visual demonstration.

Usage: python demo.py
For automated checks: python demo.py --no-browser --port 8765
No external packages, API keys, or online map requests are used.
"""
from __future__ import annotations

import argparse
import json
import math
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from experiments.integrated_benchmark import run_benchmark
from flat_astar import flat_astar, route_cost
from osm_map import dijkstra_path
from two_tier_search import prepare_hierarchy, two_tier_search
from worlds import get_world

ROOT = Path(__file__).resolve().parent
BENCHMARK_LOCK = threading.Lock()


def selected_world(options):
    return get_world(str(options.get("kind", "road")),
                     int(options.get("size", 32)), int(options.get("seed", 0)))


def execute_comparison(options):
    from worlds import closures_for
    world = selected_world(options)
    start, goal = world.endpoints(options.get("start", "Boxpark"),
                                  options.get("goal", "Port de La Mer"))
    closed, scenario_note = closures_for(world, start, goal, options.get("scenario", "none"))
    hierarchy = prepare_hierarchy(world, closed)
    flat = flat_astar(world, start, goal, closed, heuristic=world.heuristic(goal), collect_trace=True)
    tier = two_tier_search(world, start, goal, closed, hierarchy=hierarchy, collect_trace=True)
    # Independent validation occurs outside the measured query runtimes.
    optimum, _ = dijkstra_path(world.adj, start, goal, blocked=closed)
    if flat.found != (optimum is not None):
        raise AssertionError("Baseline reachability disagrees with Dijkstra.")
    if flat.found and not math.isclose(flat.cost_m, optimum, abs_tol=1e-6):
        raise AssertionError("Baseline cost disagrees with Dijkstra.")
    for result in (flat, tier):
        if result.found:
            if result.path[0] != start or result.path[-1] != goal:
                raise AssertionError("Invalid route endpoints.")
            if not math.isclose(route_cost(world, result.path, closed), result.cost_m, abs_tol=1e-6):
                raise AssertionError("Route validation failed.")
    if flat.found != tier.found:
        raise AssertionError("Fallback did not preserve baseline reachability.")
    if flat.found and tier.cost_m + 1e-6 < flat.cost_m:
        raise AssertionError("Hierarchical cost cannot improve on the verified optimum.")

    def pack(result):
        indices = world.indices
        abstract = getattr(result, "abstract_expanded", 0)
        return {
            "found": result.found, "path": [indices[n] for n in result.path],
            "trace": [indices[n] for n in result.trace],
            "cost": result.cost_m, "nodes": result.nodes_expanded,
            "abstract_nodes": abstract, "total_nodes": result.nodes_expanded + abstract,
            "runtime_ms": result.runtime_ms,
            "preprocess_ms": getattr(result, "preprocess_ms", 0.0),
            "region_path": getattr(result, "region_path", []),
            "mode": getattr(result, "mode", "Full map"),
            "attempts": getattr(result, "attempts", 1),
            "allowed": [indices[n] for n in getattr(result, "allowed_nodes", ())],
        }

    return {
        "flat": pack(flat), "tier": pack(tier),
        "start": world.indices[start], "goal": world.indices[goal],
        "blocked": [[world.indices[u], world.indices[v]] for u, v in sorted(closed)],
        "blocked_count": len(closed), "scenario_note": scenario_note,
        "region_count": len(hierarchy.adj),
        "original_route_edges_blocked": None,
        "verified": True, "unit": "m" if world.kind == "road" else "moves",
        "validation": "Both routes use open directed edges; baseline independently checked against Dijkstra.",
    }


class DemoHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Keep the launcher's terminal useful without logging large payloads.
        if "500" in str(args):
            super().log_message(format, *args)

    def send_json(self, data, status=200):
        raw = json.dumps(data, allow_nan=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/api/health":
            self.send_json({"status": "ok", "offline": True})
            return
        if url.path == "/api/scene":
            try:
                params = {k: v[0] for k, v in parse_qs(url.query).items()}
                self.send_json(selected_world(params).scene())
            except (ValueError, KeyError) as error:
                self.send_json({"error": str(error)}, 400)
            except Exception as error:
                traceback.print_exc()
                self.send_json({"error": str(error)}, 500)
            return
        files = {
            "/harshal.html": ("web/harshal.html", "text/html; charset=utf-8"),
            "/harshal.js": ("web/harshal.js", "text/javascript; charset=utf-8"),
            "/harshal.css": ("web/harshal.css", "text/css; charset=utf-8"),
            "/": ("web/harshal.html", "text/html; charset=utf-8"),
            "/reference.html": ("web/index.html", "text/html; charset=utf-8"),
            "/app.js": ("web/app.js", "text/javascript; charset=utf-8"),
            "/styles.css": ("web/styles.css", "text/css; charset=utf-8"),
            "/results/trials.csv": ("results/integrated/trials.csv", "text/csv"),
            "/results/summary.csv": ("results/integrated/summary.csv", "text/csv"),
        }
        selected = files.get(url.path)
        if selected is None or not (ROOT / selected[0]).is_file():
            self.send_error(404, "File not found")
            return
        raw = (ROOT / selected[0]).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", selected[1])
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        if selected[1] == "text/csv":
            self.send_header("Content-Disposition", f'attachment; filename="{Path(selected[0]).name}"')
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).netloc != self.headers.get("Host"):
            self.send_json({"error": "Use the demo in its own local browser tab."}, 403)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 <= length <= 10000:
                raise ValueError("Invalid request size.")
            options = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(options, dict):
                raise ValueError("Expected an options object.")
            if self.path == "/api/run":
                self.send_json(execute_comparison(options))
            elif self.path == "/api/benchmark":
                if not BENCHMARK_LOCK.acquire(blocking=False):
                    self.send_json({"error": "A benchmark is already running."}, 409)
                    return
                try:
                    self.send_json(run_benchmark(ROOT / "results" / "integrated"))
                finally:
                    BENCHMARK_LOCK.release()
            else:
                self.send_error(404)
        except (ValueError, KeyError, TypeError) as error:
            self.send_json({"error": str(error)}, 400)
        except Exception as error:
            traceback.print_exc()
            self.send_json({"error": str(error)}, 500)


def main():
    parser = argparse.ArgumentParser(description="CSCI218 offline visual demo")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), DemoHandler)
    except OSError as error:
        parser.exit(1, f"Cannot start the demo: {error}\nTry: python demo.py --port 0\n")
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"CSCI218 demo: {url}", flush=True)
    print("Keep this terminal open. Press Ctrl+C to stop.", flush=True)
    if not args.no_browser:
        threading.Timer(.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
