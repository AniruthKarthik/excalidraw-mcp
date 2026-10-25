import math
import unittest

from excalidraw_mcp.layout import grid_layout, layered_layout, linear_layout
from excalidraw_mcp.renderer import _compute_bounds
from excalidraw_mcp.service import SceneService


class LayoutAndRenderingPhase3Tests(unittest.TestCase):
    def test_p3a_linear_layout_cross_centering_horizontal(self):
        """P3A: In horizontal linear layout, nodes of different heights share the same centerline y."""
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

    def test_p3a_linear_layout_cross_centering_vertical(self):
        """P3A: In vertical linear layout, nodes of different widths share the same centerline x."""
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

    def test_p3b_dynamic_rank_gap_for_long_edge_labels(self):
        """P3B: Rank gap dynamically expands when an edge has a long descriptive label."""
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

    def test_p3c_rotation_aware_bounding_box(self):
        """P3C: _compute_bounds accurately bounds rotated elements."""
        # 200x40 rectangle at (100, 100), rotated 90 degrees (pi/2)
        # Center is (200, 120). Rotated width is 40, height is 200.
        # Rotated x bounds: [180, 220], y bounds: [20, 220].
        el = {
            "type": "rectangle",
            "x": 100.0,
            "y": 100.0,
            "width": 200.0,
            "height": 40.0,
            "angle": math.pi / 2.0,
        }
        min_x, min_y, max_x, max_y = _compute_bounds([el])

        self.assertAlmostEqual(min_x, 180.0, delta=1.0)
        self.assertAlmostEqual(max_x, 220.0, delta=1.0)
        self.assertAlmostEqual(min_y, 20.0, delta=1.0)
        self.assertAlmostEqual(max_y, 220.0, delta=1.0)

    def test_p3d_aspect_ratio_wrapping_in_draw_architecture(self):
        """P3D: draw_architecture wraps long component chains into a multi-row grid."""
        service = SceneService()
        prompt_long = (
            "box: Client, box: CDN, box: Gateway, "
            "box: Auth, box: App, box: Database"
        )
        res = service.draw_architecture(prompt_long, wrap_threshold=4)
        self.assertEqual(res["nodes"], 6)

        # Inspect resulting shapes to verify they are arranged in multiple rows
        shapes = [
            el
            for el in service.state.all()
            if el["type"] in ("rectangle", "ellipse", "diamond")
        ]
        unique_ys = {round(s["y"], -1) for s in shapes}
        self.assertGreaterEqual(len(unique_ys), 2)


if __name__ == "__main__":
    unittest.main()
