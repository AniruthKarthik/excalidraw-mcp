import io
import unittest
from PIL import Image

from excalidraw_mcp.layout import layered_layout
from excalidraw_mcp.renderer import render_scene_image, render_scene_to_png
from excalidraw_mcp.service import SceneService


class LayoutAndRenderingPhase1Tests(unittest.TestCase):
    def test_p1a_layered_cross_centering_horizontal(self):
        """P1A: Verify horizontal layered layout centers root and sink nodes along cross-axis (y)."""
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

        # Rank 0 has client, Rank 1 has srv1, srv2, srv3, Rank 2 has db
        self.assertLess(by_id["client"]["x"], by_id["srv1"]["x"])
        self.assertLess(by_id["srv1"]["x"], by_id["db"]["x"])

        # The cross span is defined by rank 1 (srv1, srv2, srv3)
        rank1_min_y = min(by_id[s]["y"] for s in ("srv1", "srv2", "srv3"))
        rank1_max_y = max(by_id[s]["y"] + by_id[s]["h"] for s in ("srv1", "srv2", "srv3"))
        midpoint_y = (rank1_min_y + rank1_max_y) / 2.0

        # Root and sink node centers should be centered around midpoint_y
        client_center_y = by_id["client"]["y"] + by_id["client"]["h"] / 2.0
        db_center_y = by_id["db"]["y"] + by_id["db"]["h"] / 2.0

        self.assertAlmostEqual(client_center_y, midpoint_y, delta=1.0)
        self.assertAlmostEqual(db_center_y, midpoint_y, delta=1.0)

    def test_p1a_layered_cross_centering_vertical(self):
        """P1A: Verify vertical layered layout centers root and sink nodes along cross-axis (x)."""
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

        # Rank 0 is at top, Rank 1 in middle, Rank 2 at bottom
        self.assertLess(by_id["root"]["y"], by_id["c1"]["y"])
        self.assertLess(by_id["c1"]["y"], by_id["sink"]["y"])

        # The cross span is defined by rank 1 (c1, c2, c3)
        rank1_min_x = min(by_id[c]["x"] for c in ("c1", "c2", "c3"))
        rank1_max_x = max(by_id[c]["x"] + by_id[c]["w"] for c in ("c1", "c2", "c3"))
        midpoint_x = (rank1_min_x + rank1_max_x) / 2.0

        root_center_x = by_id["root"]["x"] + by_id["root"]["w"] / 2.0
        sink_center_x = by_id["sink"]["x"] + by_id["sink"]["w"] / 2.0

        self.assertAlmostEqual(root_center_x, midpoint_x, delta=1.0)
        self.assertAlmostEqual(sink_center_x, midpoint_x, delta=1.0)

    def test_p1b_pil_text_centering_container_label(self):
        """P1B: Verify container-bound text is rendered centered inside its shape."""
        service = SceneService()
        res = service.add_shape(
            "rectangle",
            100.0,
            100.0,
            200.0,
            100.0,
            label="Centered Label",
            font_size=20,
        )
        doc, _ = service.state.snapshot()
        png_bytes, w, h = render_scene_image(doc, scale=1.0, padding=20)
        self.assertGreater(len(png_bytes), 0)
        img = Image.open(io.BytesIO(png_bytes))
        self.assertEqual(img.size, (w, h))

    def test_p1c_viewport_scale_clamping_for_large_diagram(self):
        """P1C: An oversized diagram spanning >4096px is downscaled to fit within 4096px."""
        service = SceneService()
        # Add shape at x=0 and shape at x=6000
        service.add_shape("rectangle", 0, 0, 100, 100, label="Start")
        service.add_shape("rectangle", 6000, 0, 100, 100, label="End")

        doc, _ = service.state.snapshot()
        # With scale=1.0, world_w = 6100 + 80 = 6180 > 4096.
        # It must clamp effective scale so img_w <= 4096.
        png_bytes, img_w, img_h = render_scene_image(doc, scale=1.0, padding=40)
        self.assertLessEqual(img_w, 4096)
        self.assertLessEqual(img_h, 4096)
        self.assertGreaterEqual(img_w, 100)
        self.assertGreaterEqual(img_h, 100)

        img = Image.open(io.BytesIO(png_bytes))
        self.assertEqual(img.size, (img_w, img_h))

    def test_p1c_viewport_centering_for_small_diagram(self):
        """P1C: A tiny diagram (<100px) is centered inside the minimum 100x100 canvas."""
        service = SceneService()
        service.add_shape("rectangle", 0, 0, 20, 20)

        doc, _ = service.state.snapshot()
        png_bytes, img_w, img_h = render_scene_image(doc, scale=1.0, padding=10)
        self.assertEqual(img_w, 100)
        self.assertEqual(img_h, 100)

        img = Image.open(io.BytesIO(png_bytes))
        self.assertEqual(img.size, (100, 100))


if __name__ == "__main__":
    unittest.main()
