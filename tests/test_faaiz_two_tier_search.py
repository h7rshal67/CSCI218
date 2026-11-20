"""Tests for faaiz_two_tier_search.py on Humna's real map (run from repo folder)."""
import unittest
from pathlib import Path

from osm_map import RoadMap
from faaiz_two_tier_search import two_tier_search

MAP = RoadMap(str(Path(__file__).resolve().parents[1] / "data" / "jumeirah.osm"))
START, GOAL = MAP.hub_node["Boxpark"], MAP.hub_node["Port de La Mer"]


def route_length(path):
    return sum(MAP.adj[a][b] for a, b in zip(path, path[1:]))


class FaaizTwoTierTests(unittest.TestCase):
    def test_route_is_valid_and_cost_matches_path(self):
        r = two_tier_search(MAP, START, GOAL)
        self.assertTrue(r["found"])
        self.assertEqual((r["path"][0], r["path"][-1]), (START, GOAL))
        self.assertAlmostEqual(r["cost_m"], route_length(r["path"]), places=3)

    def test_roadblock_is_avoided(self):
        base = two_tier_search(MAP, START, GOAL)
        mid = base["path"][len(base["path"]) // 2]
        blocked = MAP.edges_near(*MAP.coords[mid], 60)
        r = two_tier_search(MAP, START, GOAL, blocked)
        self.assertTrue(r["found"])
        self.assertFalse(any((a, b) in blocked for a, b in zip(r["path"], r["path"][1:])))

    def test_start_equals_goal(self):
        r = two_tier_search(MAP, START, START)
        self.assertTrue(r["found"])
        self.assertEqual(r["path"], [START])

    def test_unreachable_when_start_is_isolated(self):
        blocked = {(START, v) for v in MAP.adj[START]}
        r = two_tier_search(MAP, START, GOAL, blocked)
        self.assertFalse(r["found"])


if __name__ == "__main__":
    unittest.main()
