"""Standard-library unit tests: `python -m unittest -v test_flat_astar.py`."""
import math
import unittest
from types import SimpleNamespace
from flat_astar import flat_astar, route_cost


class FlatAStarTests(unittest.TestCase):
    def setUp(self):
        # Positions along an east-west street (~111 m for each 0.001 longitude).
        self.map = SimpleNamespace(
            coords={"A": (25.2, 55.2), "B": (25.2, 55.201),
                    "C": (25.2, 55.202), "D": (25.201, 55.201),
                    "E": (25.205, 55.205)},
            adj={"A": {"B": 130.0, "D": 180.0},
                 "B": {"C": 130.0}, "C": {},
                 "D": {"C": 180.0}, "E": {}}
        )

    def test_normal_shortest_path(self):
        result = flat_astar(self.map, "A", "C")
        self.assertTrue(result.found)
        self.assertEqual(result.path, ["A", "B", "C"])
        self.assertAlmostEqual(result.cost_m, 260)
        self.assertAlmostEqual(route_cost(self.map, result.path), result.cost_m)

    def test_roadblock_detour(self):
        blocked = {("B", "C")}
        result = flat_astar(self.map, "A", "C", blocked)
        self.assertEqual(result.path, ["A", "D", "C"])
        self.assertAlmostEqual(result.cost_m, 360)
        self.assertAlmostEqual(route_cost(self.map, result.path, blocked), 360)

    def test_unreachable(self):
        result = flat_astar(self.map, "A", "E")
        self.assertFalse(result.found)
        self.assertEqual(result.path, [])
        self.assertIsNone(result.cost_m)

    def test_block_all_exits(self):
        result = flat_astar(self.map, "A", "C", {("A", "B"), ("A", "D")})
        self.assertFalse(result.found)

    def test_start_equals_goal(self):
        result = flat_astar(self.map, "B", "B")
        self.assertTrue(result.found)
        self.assertEqual(result.path, ["B"])
        self.assertEqual(result.cost_m, 0)

    def test_directed_roads(self):
        self.assertFalse(flat_astar(self.map, "C", "A").found)

    def test_agrees_with_dijkstra(self):
        a = flat_astar(self.map, "A", "C")
        d = flat_astar(self.map, "A", "C", use_heuristic=False)
        self.assertAlmostEqual(a.cost_m, d.cost_m)

    def test_invalid_node(self):
        with self.assertRaises(ValueError):
            flat_astar(self.map, "missing", "C")

    def test_reopened_node_with_admissible_heuristic(self):
        # Extra case: an alternative route to a previously encountered node.
        self.map.adj["A"]["B"] = 500.0
        result = flat_astar(self.map, "A", "C")
        self.assertEqual(result.path, ["A", "D", "C"])
        self.assertAlmostEqual(result.cost_m, 360)

    def test_bad_edge_weight(self):
        self.map.adj["A"]["B"] = -3.0
        with self.assertRaises(ValueError):
            flat_astar(self.map, "A", "C")

    def test_allowed_nodes_and_trace(self):
        allowed = {"A", "D", "C"}
        result = flat_astar(self.map, "A", "C", allowed=allowed, trace=True)
        self.assertEqual(result.path, ["A", "D", "C"])
        self.assertEqual(result.nodes_expanded, len(result.expanded_trace))
        self.assertEqual(result.expanded_trace[0], "A")

    def test_allowed_nodes_must_include_endpoints(self):
        result = flat_astar(self.map, "A", "C", allowed={"B", "C"})
        self.assertFalse(result.found)
        self.assertEqual(result.nodes_expanded, 0)


if __name__ == "__main__":
    unittest.main()
