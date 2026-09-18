import unittest

from excalidraw.errors import SceneError
from excalidraw.service import SceneService


class GraphGenerationTests(unittest.TestCase):
    def graph(self):
        nodes = [{"id": "client", "label": "Client", "shape": "rectangle"},
                 {"id": "api", "label": "API", "shape": "diamond"},
                 {"id": "db", "label": "Database", "shape": "ellipse"},
                 {"id": "cache", "label": "Cache", "shape": "rectangle"}]
        edges = [{"id": "request", "source": "client", "target": "api", "label": "HTTP"},
                 {"id": "persist", "source": "api", "target": "db", "label": ""},
                 {"id": "lookup", "source": "api", "target": "cache", "label": "read"}]
        return nodes, edges

    def test_layered_graph_returns_complete_stable_mapping_and_bindings(self):
        nodes, edges = self.graph()
        service = SceneService()
        result = service.draw_graph(nodes, edges)
        self.assertEqual(set(result["node_map"]), {node["id"] for node in nodes})
        self.assertEqual(set(result["edge_map"]), {edge["id"] for edge in edges})
        self.assertEqual(result["node_map"]["client"]["label_id"] is not None, True)
        for edge in edges:
            connector = service.state.get(result["edge_map"][edge["id"]]["element_id"])
            self.assertEqual(connector["startBinding"]["elementId"],
                             result["node_map"][edge["source"]]["element_id"])
            self.assertEqual(connector["endBinding"]["elementId"],
                             result["node_map"][edge["target"]]["element_id"])
        self.assertIsNotNone(result["edge_map"]["request"]["label_id"])
        self.assertIsNone(result["edge_map"]["persist"]["label_id"])

    def test_vertical_and_horizontal_graphs_support_cycles(self):
        nodes = [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}]
        edges = [{"source": "a", "target": "b"}, {"source": "b", "target": "a"}]
        for layout in ("horizontal", "vertical"):
            service = SceneService()
            self.assertEqual(service.draw_graph(nodes, edges, layout=layout)["edges"], 2)
        with self.assertRaisesRegex(SceneError, "acyclic"):
            SceneService().draw_graph(nodes, edges)

    def test_invalid_graph_preserves_existing_scene(self):
        service = SceneService()
        service.add_text(0, 0, "existing")
        before = service.state.document()
        invalid = [
            ([{"id": "a", "label": "A"}, {"id": "a", "label": "B"}], []),
            ([{"id": "a", "label": "A"}], [{"source": "a", "target": "missing"}]),
            ([{"id": "a", "label": "", "shape": "rectangle"}], []),
        ]
        for nodes, edges in invalid:
            with self.assertRaises(SceneError):
                service.draw_graph(nodes, edges)
            self.assertEqual(service.state.document(), before)

    def test_legacy_shorthand_returns_mappings_and_no_overlap(self):
        service = SceneService()
        result = service.draw_architecture(
            "box: a label that is much longer than the old fixed layout spacing, circle: DB"
        )
        self.assertEqual(result["nodes"], 2)
        self.assertEqual(set(result["node_map"]), {"node-1", "node-2"})
        shapes = [el for el in service.state.all() if el["type"] in ("rectangle", "ellipse")]
        self.assertGreaterEqual(shapes[1]["x"], shapes[0]["x"] + shapes[0]["width"])


if __name__ == "__main__":
    unittest.main()
