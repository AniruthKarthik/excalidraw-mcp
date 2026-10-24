"""Verification and regression test suite for audit remediations.

Validates security confinement, MCP contract alignments, parser enhancements,
live server thread safety/bind failure handling, and geometry edge cases.
"""

import os
import socket
import tempfile
import unittest

from excalidraw_mcp.contracts import BatchOperation
from excalidraw_mcp.errors import SceneError
from excalidraw_mcp.importer import parse_scene_payload
from excalidraw_mcp.live_server import LiveCanvasServer
from excalidraw_mcp.mermaid import parse_mermaid
from excalidraw_mcp.service import SceneService


class AuditRemediationTests(unittest.TestCase):
    def setUp(self):
        self.service = SceneService()

    def test_importer_path_traversal_protection(self):
        """Ensure importer rejects arbitrary system paths and non-diagram extensions."""
        # Sensitive absolute file path
        if os.path.exists("/etc/passwd"):
            with self.assertRaisesRegex(SceneError, "(outside permitted|denied)"):
                parse_scene_payload("/etc/passwd")

        # Path traversal sequences
        with self.assertRaisesRegex(SceneError, "(outside permitted|denied|Unrecognized)"):
            parse_scene_payload("../../../etc/passwd")

        # Temporary file with valid extension is permitted
        with tempfile.NamedTemporaryFile("w+", suffix=".excalidraw", delete=False) as tf:
            tf.write('{"type": "excalidraw", "version": 2, "elements": []}')
            tf_path = tf.name

        try:
            doc = parse_scene_payload(tf_path)
            self.assertEqual(doc["type"], "excalidraw")
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_export_png_directory_confinement(self):
        """Ensure PNG export cannot write into arbitrary system directories."""
        self.service.add_shape("rectangle", 0, 0, 100, 100)
        with self.assertRaisesRegex(SceneError, "outside permitted"):
            self.service.export_png("exploit", directory="/etc")

        # Writing within allowed temp dir works
        with tempfile.TemporaryDirectory() as td:
            res = self.service.export_png("allowed", directory=td)
            self.assertEqual(res["status"], "png exported")
            self.assertTrue(os.path.exists(res["path"]))

    def test_get_scene_summary_code_blocks(self):
        """Ensure get_scene_summary accurately registers code blocks with dynamic line counts."""
        self.service.add_code_block(
            code="def add(a, b):\n    return a + b\n\nprint(add(1, 2))",
            language="python",
            title="Calculator",
        )
        summary = self.service.get_scene_summary()
        self.assertEqual(len(summary["code_blocks"]), 1)
        cb = summary["code_blocks"][0]
        self.assertEqual(cb["language"], "python")
        self.assertEqual(cb["title"], "Calculator")
        self.assertEqual(cb["lines_count"], 4)

    def test_code_block_text_container_alignment(self):
        """Ensure bound text in code block maintains left/top alignment."""
        res = self.service.add_code_block("line 1\nline 2")
        text_el = self.service.state.get(res["text_id"])
        self.assertEqual(text_el["textAlign"], "left")
        self.assertEqual(text_el["verticalAlign"], "top")

    def test_mermaid_multi_node_and_connectors(self):
        """Ensure Mermaid parser handles multi-node branching and joining syntax (A & B --> C & D)."""
        diagram = """graph TD
A & B --> C & D
"""
        nodes, edges, *_ = parse_mermaid(diagram)
        node_ids = {n.id for n in nodes}
        self.assertEqual(node_ids, {"A", "B", "C", "D"})
        self.assertEqual(len(edges), 4)
        edge_pairs = {(e.source, e.target) for e in edges}
        self.assertIn(("A", "C"), edge_pairs)
        self.assertIn(("A", "D"), edge_pairs)
        self.assertIn(("B", "C"), edge_pairs)
        self.assertIn(("B", "D"), edge_pairs)

    def test_batch_operation_code_block_contract(self):
        """Ensure BatchOperation contract schema accepts code block specific fields."""
        op = BatchOperation(
            action="add_code_block",
            code="console.log('hello');",
            language="javascript",
            title="Snippet",
            theme="monokai",
            line_numbers=False,
        )
        self.assertEqual(op.code, "console.log('hello');")
        self.assertEqual(op.language, "javascript")
        self.assertEqual(op.title, "Snippet")
        self.assertEqual(op.theme, "monokai")
        self.assertFalse(op.line_numbers)

    def test_live_server_port_conflict_reporting(self):
        """Ensure live server detects bind failure gracefully without hanging or false positive."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        occupied_port = sock.getsockname()[1]

        try:
            server = LiveCanvasServer(self.service)
            res = server.start(port=occupied_port)
            self.assertEqual(res["status"], "failed")
            self.assertIn("error", res)
            self.assertFalse(server.is_running)
        finally:
            sock.close()

    def test_draw_graph_parallel_edges_offset(self):
        """Ensure multiple edges connecting the same source and target are separated spatially."""
        nodes = [
            {"id": "svc_a", "label": "Service A", "shape": "rectangle"},
            {"id": "svc_b", "label": "Service B", "shape": "rectangle"},
        ]
        edges = [
            {"id": "e_grpc", "source": "svc_a", "target": "svc_b", "label": "gRPC"},
            {"id": "e_http", "source": "svc_a", "target": "svc_b", "label": "HTTP"},
        ]
        res = self.service.draw_graph(nodes, edges, layout="horizontal")
        arrow1 = self.service.state.get(res["edge_map"]["e_grpc"]["element_id"])
        arrow2 = self.service.state.get(res["edge_map"]["e_http"]["element_id"])

        # Compare coordinates: arrows should not share identical starting or ending coordinates
        self.assertNotEqual(arrow1["y"], arrow2["y"])


if __name__ == "__main__":
    unittest.main()
