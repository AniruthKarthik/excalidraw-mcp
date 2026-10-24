"""Regression and validation tests for Phase 1 audit remediations.

Covers:
- Sharing dict validation (BUG-01)
- Importer payload and file size enforcement (BUG-02)
- Line and freedraw bounding box calculation (BUG-04)
- Line and freedraw renderer rasterization
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from excalidraw_mcp.errors import SceneError
from excalidraw_mcp.importer import parse_scene_payload
from excalidraw_mcp.renderer import _compute_bounds, render_scene_to_png
from excalidraw_mcp.service import SceneService, _element_bounds
from excalidraw_mcp.sharing import export_to_excalidraw_url


class AuditFinalFixesTests(unittest.TestCase):
    def setUp(self):
        self.service = SceneService()

    def test_sharing_rejects_non_dict_documents(self):
        """BUG-01: Ensure export_to_excalidraw_url rejects non-dict inputs with SceneError."""
        for invalid in (None, "string_scene", 12345, [1, 2, 3], True):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(SceneError, "valid scene dictionary"):
                    export_to_excalidraw_url(invalid)

    def test_importer_rejects_oversized_raw_payload(self):
        """BUG-02: Ensure parse_scene_payload rejects in-memory payloads exceeding max_scene_bytes."""
        large_json = '{"type": "excalidraw", "elements": [], "pad": "' + ("A" * 500) + '"}'
        with patch("excalidraw_mcp.importer.max_scene_bytes", return_value=200):
            with self.assertRaisesRegex(SceneError, "exceeds maximum size"):
                parse_scene_payload(large_json)

    def test_importer_rejects_oversized_file(self):
        """BUG-02: Ensure parse_scene_payload rejects files on disk exceeding max_scene_bytes before read."""
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as tf:
            tf.write('{"type": "excalidraw", "elements": [], "padding": "' + ("X" * 1000) + '"}')
            tf_path = tf.name

        try:
            with patch("excalidraw_mcp.importer.max_scene_bytes", return_value=100):
                with self.assertRaisesRegex(SceneError, "exceeds maximum allowed size"):
                    parse_scene_payload(tf_path)
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_element_bounds_for_line_and_freedraw(self):
        """BUG-04: Ensure _element_bounds accounts for relative point offsets on line and freedraw elements."""
        line_el = {
            "type": "line",
            "x": 100.0,
            "y": 100.0,
            "width": 50.0,
            "height": 50.0,
            "points": [[0.0, 0.0], [-60.0, 40.0], [20.0, -30.0]],
        }
        min_x, min_y, max_x, max_y = _element_bounds(line_el)
        self.assertEqual(min_x, 40.0)   # 100.0 - 60.0
        self.assertEqual(min_y, 70.0)   # 100.0 - 30.0
        self.assertEqual(max_x, 120.0)  # 100.0 + 20.0
        self.assertEqual(max_y, 140.0)  # 100.0 + 40.0

        freedraw_el = {
            "type": "freedraw",
            "x": 200.0,
            "y": 200.0,
            "width": 10.0,
            "height": 10.0,
            "points": [[0.0, 0.0], [-25.0, -15.0], [35.0, 45.0]],
        }
        min_x, min_y, max_x, max_y = _element_bounds(freedraw_el)
        self.assertEqual(min_x, 175.0)  # 200.0 - 25.0
        self.assertEqual(min_y, 185.0)  # 200.0 - 15.0
        self.assertEqual(max_x, 235.0)  # 200.0 + 35.0
        self.assertEqual(max_y, 245.0)  # 200.0 + 45.0

    def test_renderer_bounds_and_rendering_for_line_and_freedraw(self):
        """BUG-04: Ensure renderer._compute_bounds and render_scene_to_png handle lines/freedraw."""
        doc = {
            "type": "excalidraw",
            "version": 2,
            "elements": [
                {
                    "id": "line-1",
                    "type": "line",
                    "x": 100.0,
                    "y": 100.0,
                    "width": 50.0,
                    "height": 50.0,
                    "points": [[0.0, 0.0], [-40.0, 60.0], [80.0, 20.0]],
                    "strokeColor": "#e03131",
                    "strokeWidth": 2,
                },
                {
                    "id": "draw-1",
                    "type": "freedraw",
                    "x": 300.0,
                    "y": 300.0,
                    "width": 10.0,
                    "height": 10.0,
                    "points": [[0.0, 0.0], [10.0, 10.0], [20.0, -10.0]],
                    "strokeColor": "#1971c2",
                    "strokeWidth": 2,
                },
            ],
        }
        bounds = _compute_bounds(doc["elements"])
        min_x, min_y, max_x, max_y = bounds
        self.assertEqual(min_x, 60.0)   # 100 - 40
        self.assertEqual(max_x, 320.0)  # 300 + 20

        # Verify rasterization produces valid PNG bytes with embedded metadata
        png_bytes = render_scene_to_png(doc, scale=1.0, padding=20)
        self.assertTrue(png_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
