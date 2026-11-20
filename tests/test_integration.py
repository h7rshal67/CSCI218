"""Cross-check integration behavior against independent shortest-path oracles."""
import unittest

from demo import execute_comparison
from flat_astar import flat_astar, route_cost
from osm_map import dijkstra_path
from two_tier_search import prepare_hierarchy, two_tier_search
from worlds import World, closures_for, connected_areas, grid_world, road_world


class IntegrationTests(unittest.TestCase):
    def test_grid_areas_are_connected_and_cover_every_open_cell(self):
        world = grid_world(32, 2)
        self.assertEqual(set(world.area), set(world.adj))
        for label in set(world.area.values()):
            nodes = {n for n in world.adj if world.area[n] == label}
            seen, stack = set(), [next(iter(nodes))]
            while stack:
                n = stack.pop()
                if n in seen:
                    continue
                seen.add(n)
                stack.extend(nb for nb in world.adj[n] if nb in nodes and nb not in seen)
            self.assertEqual(nodes, seen)

    def test_grid_algorithms_return_valid_paths_and_baseline_is_optimal(self):
        for size, seed in [(32, 0), (64, 4), (128, 2)]:
            with self.subTest(size=size, seed=seed):
                world = grid_world(size, seed)
                a = flat_astar(world, world.start, world.goal, heuristic=world.heuristic(world.goal))
                b = two_tier_search(world, world.start, world.goal)
                self.assertEqual(a.cost_m, world.optimum)
                self.assertTrue(b.found)
                self.assertGreaterEqual(b.cost_m, a.cost_m)
                self.assertEqual(route_cost(world, b.path), b.cost_m)

    def test_directed_closed_edges_are_not_automatically_reversed(self):
        s, g = (1, 1), (1, 2)
        world = World("grid", {s: {g: 1}, g: {s: 1}},
                      {s: s, g: g}, {s: "a", g: "b"},
                      size=4, start=s, goal=g)
        world.base_areas = world.area
        b = two_tier_search(world, s, g, {(g, s)})
        self.assertTrue(b.found)
        self.assertEqual(b.path, [s, g])

    def test_widening_can_recover_a_route_outside_the_first_corridor(self):
        a, bnode, c = (1, 1), (1, 2), (1, 3)
        world = World("grid", {a: {bnode: 1}, bnode: {c: 1}, c: {}},
                      {a: a, bnode: bnode, c: c},
                      {a: "A", bnode: "B", c: "A"}, size=5, start=a, goal=c)
        b = two_tier_search(world, a, c)
        self.assertTrue(b.found)
        self.assertEqual(b.path, [a, bnode, c])
        self.assertEqual(b.attempts, 2)
        self.assertEqual(b.mode, "Widened to neighbouring regions")

    def test_start_equals_goal(self):
        world = grid_world(32, 0)
        b = two_tier_search(world, world.start, world.start)
        self.assertTrue(b.found)
        self.assertEqual(b.path, [world.start])
        self.assertEqual(b.cost_m, 0)
        self.assertEqual(b.nodes_expanded, 0)

    def test_unreachable_and_trace_accounting(self):
        world = grid_world(32, 0)
        blocked, _ = closures_for(world, world.start, world.goal, "isolate")
        result = two_tier_search(world, world.start, world.goal, blocked, collect_trace=True)
        self.assertFalse(result.found)
        self.assertEqual(result.nodes_expanded, len(result.trace))

    def test_targeted_road_closure_forces_a_different_valid_path(self):
        world = road_world()
        start, goal = world.endpoints("Boxpark", "Port de La Mer")
        original = flat_astar(world, start, goal, heuristic=world.heuristic(goal))
        closed, _ = closures_for(world, start, goal, "targeted")
        self.assertTrue(set(zip(original.path, original.path[1:])) & closed)
        for method in ("flat", "tier"):
            res = (flat_astar(world, start, goal, closed, heuristic=world.heuristic(goal))
                   if method == "flat" else two_tier_search(world, start, goal, closed))
            self.assertTrue(res.found)
            self.assertFalse(set(zip(res.path, res.path[1:])) & closed)
            self.assertGreaterEqual(res.cost_m, original.cost_m)
            self.assertAlmostEqual(route_cost(world, res.path, closed), res.cost_m)

    def test_shared_hub_closure_is_reproduced_and_validated(self):
        result = execute_comparison({"kind": "road", "scenario": "hub"})
        self.assertTrue(result["verified"])
        self.assertEqual(result["blocked_count"], 25)
        self.assertAlmostEqual(result["flat"]["cost"], 6551.713, places=2)
        self.assertTrue(result["tier"]["found"])

    def test_map_sizes_and_seed_are_validated(self):
        for size, seed in [(16, 0), (32, -1)]:
            with self.assertRaises(ValueError):
                grid_world(size, seed)

    def test_hierarchy_rejects_different_closure_sets(self):
        world = grid_world(32, 0)
        hierarchy = prepare_hierarchy(world)
        edge = (world.start, next(iter(world.adj[world.start])))
        with self.assertRaises(ValueError):
            two_tier_search(world, world.start, world.goal, {edge}, hierarchy=hierarchy)


if __name__ == "__main__":
    unittest.main()
