"""Full-map consistency test. Run from package root: python -m unittest discover -s Code -v"""
import math, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'References'))
from osm_map import RoadMap, dijkstra_path
from first_level_search import build_hub_map, first_level_search
from flat_astar import flat_astar, route_cost

class RealMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rm=RoadMap(str(ROOT/'data'/'jumeirah.osm'))
        cls.s=cls.rm.hub_node['Boxpark']
        cls.t=cls.rm.hub_node['Port de La Mer']
        hub=first_level_search(cls.rm,build_hub_map(cls.rm),'Boxpark','Port de La Mer')
        leg=hub['legs'][len(hub['legs'])//2]
        cls.blocked=cls.rm.edges_near(*cls.rm.coords[leg[len(leg)//2]],60)

    def test_no_block_matches_dijkstra(self):
        a=flat_astar(self.rm,self.s,self.t)
        d,_=dijkstra_path(self.rm.adj,self.s,self.t)
        self.assertTrue(a.found)
        self.assertTrue(math.isclose(a.cost_m,d,abs_tol=1e-5))
        self.assertTrue(math.isclose(route_cost(self.rm,a.path),d,abs_tol=1e-5))

    def test_blocked_matches_dijkstra_and_avoids_closures(self):
        a=flat_astar(self.rm,self.s,self.t,self.blocked)
        d,_=dijkstra_path(self.rm.adj,self.s,self.t,blocked=self.blocked)
        self.assertTrue(a.found)
        self.assertTrue(math.isclose(a.cost_m,d,abs_tol=1e-5))
        self.assertTrue(math.isclose(route_cost(self.rm,a.path,self.blocked),d,abs_tol=1e-5))
        self.assertFalse(set(zip(a.path,a.path[1:])) & self.blocked)

    def test_targeted_shortest_route_closure_requires_replan(self):
        original = flat_astar(self.rm, self.s, self.t)
        # Close a real directed edge from the original flat shortest path.
        edge = (original.path[len(original.path)//2 - 1], original.path[len(original.path)//2])
        closed = {edge}
        # Close reverse too if present: physical road is obstructed in both directions.
        if edge[0] in self.rm.adj.get(edge[1], {}):
            closed.add((edge[1], edge[0]))
        replanned = flat_astar(self.rm, self.s, self.t, closed)
        dijkstra_cost, _ = dijkstra_path(self.rm.adj, self.s, self.t, blocked=closed)
        self.assertNotIn(edge, set(zip(replanned.path, replanned.path[1:])))
        self.assertEqual(replanned.found, dijkstra_cost is not None)
        if replanned.found:
            self.assertTrue(math.isclose(replanned.cost_m, dijkstra_cost, abs_tol=1e-5))
            self.assertGreaterEqual(replanned.cost_m + 1e-5, original.cost_m)
            self.assertTrue(math.isclose(route_cost(self.rm, replanned.path, closed), dijkstra_cost, abs_tol=1e-5))

    def test_humna_roadblock_does_not_cross_original_flat_route(self):
        original=flat_astar(self.rm,self.s,self.t)
        self.assertFalse(set(zip(original.path,original.path[1:])) & self.blocked)

if __name__=='__main__': unittest.main()
