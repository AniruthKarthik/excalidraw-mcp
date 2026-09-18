import unittest

from excalidraw.errors import SceneError
from layout import boundary_point, layered_layout, linear_layout, wrap_label


class LayoutTests(unittest.TestCase):
    def nodes(self):
        return [
            {"id": "client", "label": "Client", "shape": "rectangle"},
            {"id": "api", "label": "A very long API gateway label that wraps", "shape": "rectangle"},
            {"id": "db", "label": "Database", "shape": "ellipse"},
        ]

    def test_linear_layout_uses_cumulative_dimensions_without_overlap(self):
        for direction in ("horizontal", "vertical"):
            placed = linear_layout(self.nodes(), direction, gap=50)
            for left, right in zip(placed, placed[1:]):
                if direction == "horizontal":
                    self.assertGreaterEqual(right["x"], left["x"] + left["w"] + 50)
                else:
                    self.assertGreaterEqual(right["y"], left["y"] + left["h"] + 50)
            self.assertIn("\n", placed[1]["label"])

    def test_layered_layout_supports_branches_and_is_deterministic(self):
        nodes = self.nodes() + [{"id": "cache", "label": "Cache", "shape": "diamond"}]
        edges = [{"source": "client", "target": "api"},
                 {"source": "api", "target": "db"},
                 {"source": "api", "target": "cache"}]
        first = layered_layout(nodes, edges)
        self.assertEqual(first, layered_layout(nodes, edges))
        lookup = {node["id"]: node for node in first}
        self.assertLess(lookup["client"]["x"], lookup["api"]["x"])
        self.assertLess(lookup["api"]["x"], lookup["db"]["x"])
        self.assertNotEqual(lookup["db"]["y"], lookup["cache"]["y"])

    def test_layered_layout_rejects_cycles(self):
        nodes = self.nodes()[:2]
        with self.assertRaisesRegex(SceneError, "acyclic"):
            layered_layout(nodes, [{"source": "client", "target": "api"},
                                   {"source": "api", "target": "client"}])

    def test_boundary_points_lie_on_shape_edges(self):
        source = {"shape": "rectangle", "x": 0, "y": 0, "w": 100, "h": 100}
        target = {"shape": "rectangle", "x": 300, "y": 0, "w": 100, "h": 100}
        self.assertEqual(boundary_point(source, target), (100, 50))
        ellipse = {"shape": "ellipse", "x": 0, "y": 0, "w": 200, "h": 100}
        self.assertEqual(boundary_point(ellipse, target), (200, 50))

    def test_wrap_label_preserves_paragraphs_and_long_words(self):
        wrapped = wrap_label("alpha beta\nsupercalifragilisticexpialidocious", 10)
        self.assertTrue(all(len(line) <= 10 for line in wrapped.splitlines()))


if __name__ == "__main__":
    unittest.main()
