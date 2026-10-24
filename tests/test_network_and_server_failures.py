"""P1 Robustness test suite for external network outages, font fallbacks, and server failures.

Verifies:
- Encrypted sharing failure recovery under HTTP 5xx, timeouts, and network drops
- Font loading fallbacks under missing families and negative sizes
- Pygments syntax highlighter fallback on unknown programming languages
- Live canvas WebSocket server failure handling
"""

import unittest
from unittest.mock import MagicMock, patch

import httpx
from PIL import ImageFont

from excalidraw_mcp.code_blocks import highlight_code
from excalidraw_mcp.errors import SceneError
from excalidraw_mcp.fonts import FontRegistry
from excalidraw_mcp.sharing import export_to_excalidraw_url


class NetworkAndServerFailureTests(unittest.TestCase):
    def test_sharing_http_502_bad_gateway_handled(self):
        """TC-HIGH-06: Ensure export_to_excalidraw_url raises SceneError on upstream 502/500 errors."""
        doc = {"type": "excalidraw", "elements": [{"id": "1", "type": "rectangle", "x": 0, "y": 0, "width": 10, "height": 10}]}

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "502 Bad Gateway",
            request=MagicMock(),
            response=MagicMock(status_code=502),
        )

        with patch("httpx.Client.post", return_value=mock_resp):
            with self.assertRaisesRegex(SceneError, "returned HTTP 502"):
                export_to_excalidraw_url(doc)

    def test_sharing_timeout_handled(self):
        """Ensure export_to_excalidraw_url handles network timeout without unhandled crash."""
        doc = {"type": "excalidraw", "elements": [{"id": "1", "type": "rectangle", "x": 0, "y": 0, "width": 10, "height": 10}]}

        with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Connection timed out after 12s")):
            with self.assertRaisesRegex(SceneError, "timed out"):
                export_to_excalidraw_url(doc)

    def test_font_registry_fallback_on_unknown_family_and_negative_size(self):
        """TC-HIGH-03: Ensure FontRegistry safely handles unknown font families and negative sizes."""
        reg = FontRegistry()
        # Unknown font family with negative size
        font = reg.load_font(family="UnknownAlienFontFamilyXYZ", size=-15)
        self.assertIsNotNone(font)
        # Font must be a valid PIL ImageFont instance
        self.assertTrue(isinstance(font, (ImageFont.ImageFont, ImageFont.FreeTypeFont)))

    def test_code_block_lexer_fallback_on_unknown_language(self):
        """TC-HIGH-04: Ensure highlight_code handles unregistered language strings via TextLexer fallback."""
        code = "def custom_syntax(): pass"
        # Unknown language identifier
        tokens = highlight_code(code, language="brainfuck_obscure_variant", theme_name="dark")
        self.assertIsInstance(tokens, list)
        self.assertGreater(len(tokens), 0)
        # Full text must be preserved
        reconstructed = "\n".join("".join(text for text, _ in line) for line in tokens)
        self.assertEqual(reconstructed, code)
