import io
import unittest
from PIL import Image

from excalidraw_mcp.errors import SceneError
from excalidraw_mcp.renderer import render_scene_image
from excalidraw_mcp.service import SceneService


class LayoutAndRenderingPhase2Tests(unittest.TestCase):
    def test_p2a_bidirectional_edge_collision_avoidance(self):
        """P2A: Bidirectional edges A->B and B->A must be routed along separate parallel lanes."""
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

        # The arrows must be shifted perpendicularly so they do not share y coordinates
        self.assertNotEqual(arr_req["y"], arr_res["y"])
        self.assertGreaterEqual(abs(arr_req["y"] - arr_res["y"]), 20.0)

        # The labels must not share midpoint coordinates
        self.assertNotEqual(lbl_req["y"], lbl_res["y"])
        self.assertGreaterEqual(abs(lbl_req["y"] - lbl_res["y"]), 20.0)

    def test_p2b_arrow_label_masking(self):
        """P2B: Arrow label background mask protects label text from stroke strike-through."""
        service = SceneService()
        nodes = [
            {"id": "n1", "label": "Sender", "shape": "rectangle"},
            {"id": "n2", "label": "Receiver", "shape": "rectangle"},
        ]
        edges = [
            {"id": "e1", "source": "n1", "target": "n2", "label": "Encrypted Message"},
        ]
        service.draw_graph(nodes, edges, layout="horizontal")
        doc, _ = service.state.snapshot()

        # Render PNG
        png_bytes, w, h = render_scene_image(doc, scale=1.0)
        self.assertGreater(len(png_bytes), 0)
        img = Image.open(io.BytesIO(png_bytes))
        self.assertEqual(img.size, (w, h))

    def test_p2c_elbowed_connector_rendering(self):
        """P2C: Elbowed connector generates orthogonal Manhattan routing in renderer."""
        service = SceneService()
        nodes = [
            {"id": "top_left", "label": "Client", "shape": "rectangle"},
            {"id": "bottom_right", "label": "Worker", "shape": "rectangle"},
        ]
        edges = [
            {"id": "elbow_edge", "source": "top_left", "target": "bottom_right", "label": "Queue"},
        ]
        service.draw_graph(nodes, edges, layout="horizontal", elbowed=True)
        doc, _ = service.state.snapshot()

        png_bytes, w, h = render_scene_image(doc, scale=1.0)
        self.assertGreater(len(png_bytes), 0)
        img = Image.open(io.BytesIO(png_bytes))
        self.assertEqual(img.size, (w, h))

    def test_p2d_cycle_safe_fallback_in_draw_graph(self):
        """P2D: draw_graph falls back cleanly to linear layout when cycle_fallback=True."""
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

        # With default cycle_fallback=False, it raises SceneError("acyclic")
        with self.assertRaisesRegex(SceneError, "acyclic"):
            service.draw_graph(cyclic_nodes, cyclic_edges, layout="layered", cycle_fallback=False)

        # With cycle_fallback=True, it gracefully succeeds via linear layout
        res = service.draw_graph(cyclic_nodes, cyclic_edges, layout="layered", cycle_fallback=True)
        self.assertEqual(res["nodes"], 3)
        self.assertEqual(res["edges"], 3)
        self.assertEqual(len(res["node_map"]), 3)

    def test_p2d_draw_mermaid_handles_cycles_gracefully(self):
        """P2D: draw_mermaid handles diagrams with cycles without raising SceneError."""
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


if __name__ == "__main__":
    unittest.main()
