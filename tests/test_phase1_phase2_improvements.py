"""Tests for Phase 1 and Phase 2 improvements.

Verifies:
- Font LRU cache invalidation on discover(force=True) (Phase 1)
- Viewport updates decoupled from undo history (Phase 1)
- Unsupported Mermaid diagram header detection and actionable errors (Phase 2)
- ArchitectureResult next_step export options and tool description clarity (Phase 2)
"""

import asyncio
import unittest

from excalidraw_mcp.errors import SceneError
from excalidraw_mcp.fonts import FontRegistry
from excalidraw_mcp.mermaid import parse_mermaid
from excalidraw_mcp.server import create_server
from excalidraw_mcp.service import SceneService


class Phase1Phase2Tests(unittest.TestCase):
    def setUp(self):
        self.service = SceneService()

    def test_font_cache_clear_on_discover_force(self):
        """Phase 1: Ensure discover(force=True) invalidates load_font LRU cache."""
        reg = FontRegistry()
        reg.load_font("sans-serif", 14)
        info1 = reg.load_font.cache_info()
        self.assertGreaterEqual(info1.currsize, 1)

        # Force discovery should clear cache
        reg.discover(force=True)
        info2 = reg.load_font.cache_info()
        self.assertEqual(info2.currsize, 0)

    def test_viewport_decoupled_from_undo_history(self):
        """Phase 1: Verify set_viewport and focus_elements do not pollute undo history."""
        # 1. Add a shape (should be in history)
        r = self.service.add_shape("rectangle", 100, 100, 200, 100, label="Box 1")
        self.assertEqual(self.service.state.history_depth, 1)

        # 2. Set viewport (should NOT increment history_depth)
        self.service.set_viewport(scroll_x=50.0, scroll_y=50.0, zoom=1.5)
        self.assertEqual(self.service.state.history_depth, 1)

        # 3. Focus elements (should NOT increment history_depth)
        self.service.focus_elements([r["rectangle_id"]])
        self.assertEqual(self.service.state.history_depth, 1)

        # 4. Calling undo should revert the shape creation, not the viewport pan
        undo_res = self.service.undo()
        self.assertEqual(undo_res["status"], "undone")
        # Scene should now have 0 active shapes
        doc = self.service.state.document()
        active_shapes = [el for el in doc["elements"] if not el.get("isDeleted")]
        self.assertEqual(len(active_shapes), 0)

    def test_mermaid_actionable_error_on_unsupported_diagrams(self):
        """Phase 2: Ensure non-flowchart Mermaid diagram headers produce actionable errors."""
        unsupported_snippets = [
            "sequenceDiagram\nAlice->>Bob: Hello",
            "classDiagram\nclass Animal",
            "stateDiagram\n[*] --> Still",
            "stateDiagram-v2\n[*] --> State1",
            "erDiagram\nCUSTOMER ||--o{ ORDER : places",
            "gantt\ntitle A Gantt Diagram",
            "gitGraph\ncommit",
        ]
        for snippet in unsupported_snippets:
            with self.subTest(diagram=snippet.splitlines()[0]):
                with self.assertRaisesRegex(
                    SceneError,
                    r"are not supported yet\. Only flowchart and graph diagrams",
                ):
                    parse_mermaid(snippet)

    def test_architecture_result_and_inspection_tool_descriptions(self):
        """Phase 2: Verify ArchitectureResult next_step and inspection tool descriptions."""
        arch = self.service.draw_architecture("box: Client, box: Server")
        self.assertIn("export_to_excalidraw_url", arch["next_step"])

        mcp = create_server(self.service)
        tools = asyncio.run(mcp.list_tools())
        tool_map = {t.name: t.description for t in tools}

        self.assertIn("get_scene_summary", tool_map)
        self.assertIn("describe_scene", tool_map)
        # Verify descriptions guide models on quantitative vs qualitative roles
        self.assertIn("numerical metrics", tool_map["get_scene_summary"])
        self.assertIn("natural language prose", tool_map["describe_scene"])
