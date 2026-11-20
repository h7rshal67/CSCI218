"""Dependency-free directed-graph integration tests for Faaiz's two-tier A*."""
import unittest
from types import SimpleNamespace
from faaiz_two_tier_search import two_tier_search, detailed_astar


class TwoTierSyntheticTests(unittest.TestCase):
    def setUp(self):
        self.map = SimpleNamespace(
            coords={'A': (25.2, 55.2), 'B': (25.2, 55.201),
                    'C': (25.2, 55.202), 'D': (25.201, 55.201)},
            adj={'A': {'B': 130., 'D': 170.}, 'B': {'C': 130.},
                 'C': {}, 'D': {'C': 170.}},
            area={'A': 'west', 'B': 'mid', 'C': 'east', 'D': 'south'},
        )

    def test_route_and_count_fields(self):
        r = two_tier_search(self.map, 'A', 'C')
        self.assertEqual(r['path'], ['A', 'B', 'C'])
        self.assertEqual(r['cost_m'], 260.)
        self.assertEqual(r['total_nodes_expanded'], r['nodes_expanded'] + r['region_nodes_expanded'])
        self.assertEqual(r['nodes_expanded'], sum(a['nodes_expanded'] for a in r['attempt_expansions']))

    def test_directed_closure_detours(self):
        r = two_tier_search(self.map, 'A', 'C', {('B', 'C')})
        self.assertEqual(r['path'], ['A', 'D', 'C'])
        self.assertEqual(r['cost_m'], 340.)

    def test_unreachable(self):
        r = two_tier_search(self.map, 'A', 'C', {('A', 'B'), ('A', 'D')})
        self.assertFalse(r['found'])
        self.assertIsNone(r['cost_m'])

    def test_identical_endpoint(self):
        r = two_tier_search(self.map, 'A', 'A')
        self.assertEqual(r['path'], ['A'])
        self.assertEqual(r['cost_m'], 0.)

    def test_invalid_nodes(self):
        with self.assertRaises(ValueError):
            two_tier_search(self.map, 'X', 'C')

    def test_allowed_filter_rejects_start_outside(self):
        path, cost, expanded = detailed_astar(self.map, 'A', 'C', allowed={'B', 'C'})
        self.assertIsNone(path)
        self.assertEqual(expanded, 0)


if __name__ == '__main__':
    unittest.main()
