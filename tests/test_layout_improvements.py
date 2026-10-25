import unittest

from excalidraw_mcp.errors import SceneError
from excalidraw_mcp.layout import layered_layout, linear_layout
from excalidraw_mcp.service import SceneService


class LayoutImprovementsTests(unittest.TestCase):
    def test_layered_cross_centering_horizontal(self):
        """Verify horizontal layered layout centers root and sink nodes along cross-axis (y)."""
        nodes = [
            {"id": "client", "label": "Client", "shape": "rectangle"},
            {"id": "srv1", "label": "Service 1", "shape": "rectangle"},
            {"id": "srv2", "label": "Service 2", "shape": "rectangle"},
            {"id": "srv3", "label": "Service 3", "shape": "rectangle"},
            {"id": "db", "label": "Database", "shape": "ellipse"},
        ]
        edges = [
            {"source": "client", "target": "srv1"},
            {"source": "client", "target": "srv2"},
            {"source": "client", "target": "srv3"},
            {"source": "srv1", "target": "db"},
            {"source": "srv2", "target": "db"},
            {"source": "srv3", "target": "db"},
        ]

        placed = layered_layout(nodes, edges, direction="horizontal", rank_gap=120, node_gap=50)
        by_id = {n["id"]: n for n in placed}

        self.assertLess(by_id["client"]["x"], by_id["srv1"]["x"])
        self.assertLess(by_id["srv1"]["x"], by_id["db"]["x"])

        rank1_min_y = min(by_id[s]["y"] for s in ("srv1", "srv2", "srv3"))
        rank1_max_y = max(by_id[s]["y"] + by_id[s]["h"] for s in ("srv1", "srv2", "srv3"))
        midpoint_y = (rank1_min_y + rank1_max_y) / 2.0

        client_center_y = by_id["client"]["y"] + by_id["client"]["h"] / 2.0
        db_center_y = by_id["db"]["y"] + by_id["db"]["h"] / 2.0

        self.assertAlmostEqual(client_center_y, midpoint_y, delta=1.0)
        self.assertAlmostEqual(db_center_y, midpoint_y, delta=1.0)

    def test_layered_cross_centering_vertical(self):
        """Verify vertical layered layout centers root and sink nodes along cross-axis (x)."""
        nodes = [
            {"id": "root", "label": "Root", "shape": "rectangle"},
            {"id": "c1", "label": "Worker 1", "shape": "rectangle"},
            {"id": "c2", "label": "Worker 2", "shape": "rectangle"},
            {"id": "c3", "label": "Worker 3", "shape": "rectangle"},
            {"id": "sink", "label": "Sink", "shape": "rectangle"},
        ]
        edges = [
            {"source": "root", "target": "c1"},
            {"source": "root", "target": "c2"},
            {"source": "root", "target": "c3"},
            {"source": "c1", "target": "sink"},
            {"source": "c2", "target": "sink"},
            {"source": "c3", "target": "sink"},
        ]

        placed = layered_layout(nodes, edges, direction="vertical", rank_gap=120, node_gap=60)
        by_id = {n["id"]: n for n in placed}

        self.assertLess(by_id["root"]["y"], by_id["c1"]["y"])
        self.assertLess(by_id["c1"]["y"], by_id["sink"]["y"])

        rank1_min_x = min(by_id[c]["x"] for c in ("c1", "c2", "c3"))
        rank1_max_x = max(by_id[c]["x"] + by_id[c]["w"] for c in ("c1", "c2", "c3"))
        midpoint_x = (rank1_min_x + rank1_max_x) / 2.0

        root_center_x = by_id["root"]["x"] + by_id["root"]["w"] / 2.0
        sink_center_x = by_id["sink"]["x"] + by_id["sink"]["w"] / 2.0

        self.assertAlmostEqual(root_center_x, midpoint_x, delta=1.0)
        self.assertAlmostEqual(sink_center_x, midpoint_x, delta=1.0)

    def test_linear_layout_cross_centering_horizontal(self):
        """In horizontal linear layout, nodes of different heights share the same centerline y."""
        nodes = [
            {"id": "n1", "label": "Short", "shape": "rectangle"},
            {
                "id": "n2",
                "label": "Tall\nMulti-line\nDetailed\nComponent",
                "shape": "rectangle",
            },
            {"id": "n3", "label": "Single", "shape": "ellipse"},
        ]
        placed = linear_layout(nodes, direction="horizontal")
        center_ys = [n["y"] + n["h"] / 2.0 for n in placed]
        for cy in center_ys[1:]:
            self.assertAlmostEqual(cy, center_ys[0], places=5)

    def test_linear_layout_cross_centering_vertical(self):
        """In vertical linear layout, nodes of different widths share the same centerline x."""
        nodes = [
            {"id": "n1", "label": "Short", "shape": "rectangle"},
            {
                "id": "n2",
                "label": "Very Wide Database Cluster Engine",
                "shape": "rectangle",
            },
            {"id": "n3", "label": "Mid", "shape": "diamond"},
        ]
        placed = linear_layout(nodes, direction="vertical")
        center_xs = [n["x"] + n["w"] / 2.0 for n in placed]
        for cx in center_xs[1:]:
            self.assertAlmostEqual(cx, center_xs[0], places=5)

    def test_dynamic_rank_gap_for_long_edge_labels(self):
        """Rank gap dynamically expands when an edge has a long descriptive label."""
        nodes = [
            {"id": "client", "label": "Client", "shape": "rectangle"},
            {"id": "server", "label": "Server", "shape": "rectangle"},
        ]
        short_edges = [{"source": "client", "target": "server", "label": "OK"}]
        long_edges = [
            {
                "source": "client",
                "target": "server",
                "label": "Extremely Long Cryptographic Authentication Token",
            }
        ]

        placed_short = layered_layout(nodes, short_edges, rank_gap=180)
        placed_long = layered_layout(nodes, long_edges, rank_gap=180)

        gap_short = placed_short[1]["x"] - (placed_short[0]["x"] + placed_short[0]["w"])
        gap_long = placed_long[1]["x"] - (placed_long[0]["x"] + placed_long[0]["w"])

        self.assertGreater(gap_long, gap_short)
        self.assertGreaterEqual(gap_long, 300)

    def test_bidirectional_edge_collision_avoidance(self):
        """Bidirectional edges A->B and B->A must be routed along separate parallel lanes."""
        service = SceneService()
        nodes = [
            {"id": "A", "label": "Service A", "shape": "rectangle"},
            {"id": "B", "label": "Service B", "shape": "rectangle"},
        ]
        edges = [
            {"id": "e_req", "source": "A", "target": "B", "label": "Request"},
            {"id": "e_res", "source": "B", "target": "A", "label": "Response"},
        ]
        res = service.draw_graph(nodes, edges, layout="horizontal")
        arr_req = service.state.get(res["edge_map"]["e_req"]["element_id"])
        arr_res = service.state.get(res["edge_map"]["e_res"]["element_id"])

        lbl_req = service.state.get(res["edge_map"]["e_req"]["label_id"])
        lbl_res = service.state.get(res["edge_map"]["e_res"]["label_id"])

        self.assertNotEqual(arr_req["y"], arr_res["y"])
        self.assertGreaterEqual(abs(arr_req["y"] - arr_res["y"]), 20.0)

        self.assertNotEqual(lbl_req["y"], lbl_res["y"])
        self.assertGreaterEqual(abs(lbl_req["y"] - lbl_res["y"]), 20.0)

    def test_cycle_safe_fallback_in_draw_graph(self):
        """draw_graph falls back cleanly to linear layout when cycle_fallback=True."""
        service = SceneService()
        cyclic_nodes = [
            {"id": "n1", "label": "Node 1"},
            {"id": "n2", "label": "Node 2"},
            {"id": "n3", "label": "Node 3"},
        ]
        cyclic_edges = [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n3"},
            {"source": "n3", "target": "n1"},
        ]

        with self.assertRaisesRegex(SceneError, "acyclic"):
            service.draw_graph(cyclic_nodes, cyclic_edges, layout="layered", cycle_fallback=False)

        res = service.draw_graph(cyclic_nodes, cyclic_edges, layout="layered", cycle_fallback=True)
        self.assertEqual(res["nodes"], 3)
        self.assertEqual(res["edges"], 3)
        self.assertEqual(len(res["node_map"]), 3)

    def test_draw_mermaid_handles_cycles_gracefully(self):
        """draw_mermaid handles diagrams with cycles without raising SceneError."""
        service = SceneService()
        mermaid_code = """
        graph LR
            A[Service A] --> B[Service B]
            B --> C[Service C]
            C --> A
        """
        res = service.draw_mermaid(mermaid_code)
        self.assertEqual(res["nodes"], 3)
        self.assertEqual(res["edges"], 3)

    def test_aspect_ratio_wrapping_in_draw_architecture(self):
        """draw_architecture wraps long component chains into a multi-row grid."""
        service = SceneService()
        prompt_long = (
            "box: Client, box: CDN, box: Gateway, "
            "box: Auth, box: App, box: Database"
        )
        res = service.draw_architecture(prompt_long, wrap_threshold=4)
        self.assertEqual(res["nodes"], 6)

        shapes = [
            el
            for el in service.state.all()
            if el["type"] in ("rectangle", "ellipse", "diamond")
        ]
        unique_ys = {round(s["y"], -1) for s in shapes}
        self.assertGreaterEqual(len(unique_ys), 2)


if __name__ == "__main__":
    unittest.main()
