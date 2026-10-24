"""P2 and P3 boundary condition test suite for validators, label wrappers, and format helpers.

Verifies:
- Hex color validation boundaries (3-digit, 6-digit, 8-digit alpha, transparent, invalid characters)
- Word-wrapping on unbroken 500-character tokens
- focus_elements behavior on empty scenes
- Code block container alignment preservation
- Diagram design guide topic lookups
"""

import unittest

from excalidraw_mcp.design_guide import get_diagram_guide
from excalidraw_mcp.elements import bind_text, rect, text
from excalidraw_mcp.errors import SceneError
from excalidraw_mcp.layout import wrap_label
from excalidraw_mcp.service import SceneService
from excalidraw_mcp.validation import valid_color


class BoundaryConditionsTests(unittest.TestCase):
    def setUp(self):
        self.service = SceneService()

    def test_valid_color_boundaries(self):
        """TC-MED-01: Verify valid_color acceptance and rejection boundaries."""
        # Valid cases (3-8 hex chars or transparent)
        valid_cases = ["#fff", "#FFF", "#ffff", "#1e1e1e", "#AABBCC", "#1e1e1eff", "#00000000", "transparent"]
        for c in valid_cases:
            with self.subTest(color=c):
                self.assertTrue(valid_color(c))

        # Invalid cases
        invalid_cases = ["#ff", "#123456789", "#12345g", "blue", "rgb(0,0,0)", "", None, 12345, True]
        for c in invalid_cases:
            with self.subTest(color=c):
                self.assertFalse(valid_color(c))

    def test_wrap_label_unbroken_long_token(self):
        """TC-MED-06: Ensure wrap_label breaks unbroken 500-character tokens into <=24 char lines."""
        long_token = "A" * 500
        wrapped = wrap_label(long_token, max_chars=24)
        lines = wrapped.splitlines()
        self.assertGreater(len(lines), 20)
        for line in lines:
            self.assertLessEqual(len(line), 24)

    def test_focus_elements_empty_scene_zero_division_safe(self):
        """TC-MED-03: Ensure focus_elements on an empty scene resets viewport safely without ZeroDivisionError."""
        res = self.service.focus_elements()
        self.assertEqual(res["status"], "focused")
        self.assertEqual(res["zoom"], 1.0)
        self.assertEqual(res["focused_element_ids"], [])

    def test_bind_text_code_block_vs_shape_alignment(self):
        """TC-MED-05: Ensure bind_text preserves left-alignment for code blocks and center for shapes."""
        # 1. Regular rectangle container
        r = rect(0, 0, 100, 100)
        t1 = text(0, 0, "Shape Label")
        bind_text(t1, r)
        self.assertEqual(t1["textAlign"], "center")
        self.assertEqual(t1["verticalAlign"], "middle")

        # 2. Code block container
        cb = rect(0, 0, 300, 200)
        cb["customData"] = {"type": "code_block"}
        t2 = text(0, 0, "def code(): pass")
        bind_text(t2, cb)
        self.assertEqual(t2["textAlign"], "left")
        self.assertEqual(t2["verticalAlign"], "top")

    def test_diagram_guide_unknown_topic_fallback(self):
        """TC-LOW-01: Ensure get_diagram_guide on an unknown topic raises helpful SceneError."""
        with self.assertRaisesRegex(SceneError, "Unknown topic 'nonexistent_diagram_topic'"):
            get_diagram_guide("nonexistent_diagram_topic")
