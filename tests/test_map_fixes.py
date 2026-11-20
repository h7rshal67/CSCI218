"""Checks for the map, hubs and hub-level search (Humna's component).

Run from the project folder:  python -m unittest discover -s tests -v
"""
import math
import unittest
import warnings
from pathlib import Path

from first_level_search import build_hub_map, first_level_search
from osm_map import HUBS, RoadMap, haversine_m

ROOT = Path(__file__).resolve().parents[1]
START, GOAL = "Boxpark", "Port de La Mer"


class MapAndHubTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            cls.rm = RoadMap(str(ROOT / "data" / "jumeirah.osm"))
        cls.warnings = [str(w.message) for w in caught]
        cls.hub_map = build_hub_map(cls.rm)

    def test_all_eight_hubs_are_placed_on_different_road_nodes(self):
        self.assertEqual(set(self.rm.hub_node), set(HUBS))
        self.assertEqual(len(set(self.rm.hub_node.values())), len(HUBS))

    def test_every_hub_has_its_own_area(self):
        self.assertEqual(set(self.rm.area.values()), set(HUBS))
        for hub, node in self.rm.hub_node.items():
            self.assertEqual(self.rm.area[node], hub)

    def test_ambiguous_hub_name_is_pinned_not_guessed(self):
        # "Mercato Shopping Mall" occurs at two different places in the OSM file.
        self.assertIn("Mercato Shopping Mall", self.rm.ambiguous_names)
        self.assertEqual(HUBS["Mercato Mall"][0], "latlon")
        self.assertEqual(self.warnings, [])      # no hub depends on an ambiguous name
        lat, lon = self.rm.hub_pos["Mercato Mall"]
        self.assertAlmostEqual(lat, 25.2162583, places=6)
        self.assertAlmostEqual(lon, 55.2532819, places=6)

    def test_hubs_are_close_to_a_road(self):
        for hub, metres in self.rm.hub_snap_m.items():
            self.assertLess(metres, 200, hub)

    def test_hub_search_matches_plain_search_for_every_pair(self):
        for s in self.hub_map:
            for g in self.hub_map:
                if s == g:
                    continue
                a = first_level_search(self.rm, self.hub_map, s, g)
                d = first_level_search(self.rm, self.hub_map, s, g, use_heuristic=False)
                self.assertTrue(math.isclose(a["cost_m"], d["cost_m"], abs_tol=1e-6), (s, g))

    def test_guess_never_overestimates(self):
        for s in self.hub_map:
            for g in self.hub_map:
                if s == g:
                    continue
                true_cost = first_level_search(self.rm, self.hub_map, s, g, use_heuristic=False)["cost_m"]
                guess = haversine_m(*self.rm.coords[self.rm.hub_node[s]],
                                    *self.rm.coords[self.rm.hub_node[g]])
                self.assertLessEqual(guess, true_cost + 1e-6, (s, g))

    def test_unknown_hub_gives_a_clear_error(self):
        with self.assertRaises(ValueError):
            first_level_search(self.rm, self.hub_map, START, "Nowhere")

    def test_start_equals_goal(self):
        r = first_level_search(self.rm, self.hub_map, START, START)
        self.assertTrue(r["found"])
        self.assertEqual(r["cost_m"], 0)


class RoadblockScenarioTests(unittest.TestCase):
    """The roadblock settings documented in MAP_AND_ROADBLOCKS.md must stay reproducible."""

    @classmethod
    def setUpClass(cls):
        cls.rm = RoadMap(str(ROOT / "data" / "jumeirah.osm"))
        cls.hub_map = build_hub_map(cls.rm)
        cls.base = first_level_search(cls.rm, cls.hub_map, START, GOAL)

    def closed_roads(self, radius):
        leg = self.base["legs"][len(self.base["legs"]) // 2]
        spot = leg[len(leg) // 2]
        return self.rm.edges_near(*self.rm.coords[spot], radius)

    def test_route_without_roadblock(self):
        self.assertEqual(self.base["macro_path"],
                         ["Boxpark", "Carrefour Market", "La Mer", "Port de La Mer"])
        self.assertEqual(round(self.base["cost_m"]), 7213)

    def test_60_m_roadblock(self):
        closed = self.closed_roads(60)
        self.assertEqual(len(closed), 25)
        r = first_level_search(self.rm, build_hub_map(self.rm, closed), START, GOAL)
        self.assertEqual(round(r["cost_m"]), 7239)
        self.assertFalse({e for leg in r["legs"] for e in zip(leg, leg[1:])} & closed)

    def test_150_m_roadblock(self):
        closed = self.closed_roads(150)
        self.assertEqual(len(closed), 181)
        r = first_level_search(self.rm, build_hub_map(self.rm, closed), START, GOAL)
        self.assertEqual(round(r["cost_m"]), 7346)
        self.assertFalse({e for leg in r["legs"] for e in zip(leg, leg[1:])} & closed)

    def test_roadblock_closes_both_directions(self):
        closed = self.closed_roads(60)
        for u, v in closed:
            if u in self.rm.adj.get(v, {}):
                self.assertIn((v, u), closed)


if __name__ == "__main__":
    unittest.main()
