import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastmcp.exceptions import ToolError

import main
from excalidraw.elements import rect
from excalidraw.errors import SceneError
from excalidraw.scene import new_document
from excalidraw.state import SceneState


class ReplacementTests(unittest.TestCase):
    def setUp(self):
        self.scene = SceneState()
        self.original = new_document([rect(0, 0, 100, 100)])
        self.original["appState"] = {"viewBackgroundColor": "#123456"}
        self.original["files"] = {"asset": {"dataURL": "data:image/png;base64,example"}}
        self.original["custom"] = "preserve me"
        self.scene.replace(self.original)
        active = patch.object(main, "scene", self.scene)
        active.start()
        self.addCleanup(active.stop)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        env = patch.dict(os.environ, {"EXCALIDRAW_SCENE_DIR": str(self.root)})
        env.start()
        self.addCleanup(env.stop)

    def test_blank_architecture_keeps_current_document(self):
        for prompt in ("", " \n, ", "box:", "-*", "box: API, circle:"):
            with self.subTest(prompt=prompt):
                with self.assertRaises(ToolError):
                    main.draw_architecture(prompt)
                self.assertEqual(self.scene.document(), self.original)

    def test_construction_failure_keeps_current_document(self):
        with patch.object(main, "text", side_effect=RuntimeError("construction failed")):
            with self.assertRaises(RuntimeError):
                main.draw_architecture("box: API, box: Database")
        self.assertEqual(self.scene.document(), self.original)

    def test_failed_load_keeps_current_document(self):
        for document in ({**self.original, "elements": [self.original["elements"][0], {}]},
                         {**self.original, "elements": None}, {"unrelated": "JSON"}):
            (self.root / "bad.excalidraw").write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(ToolError):
                main.load("bad")
            self.assertEqual(self.scene.document(), self.original)
        with self.assertRaises(ToolError):
            main.load("absent")
        self.assertEqual(self.scene.document(), self.original)

    def test_tool_roundtrip_preserves_metadata_and_assets(self):
        result = main.save("roundtrip")
        self.assertTrue(Path(result["path"]).is_absolute())
        self.scene.clear()
        main.load("roundtrip")
        main.move(self.original["elements"][0]["id"], 10, 20)
        main.save("roundtrip", overwrite=True)
        document = json.loads((self.root / "roundtrip.excalidraw").read_text())
        self.assertEqual(document["files"], self.original["files"])
        self.assertEqual(document["appState"], self.original["appState"])
        self.assertEqual(document["custom"], "preserve me")
        self.assertEqual(document["elements"][0]["x"], 10)

    def test_tool_save_reports_overwrite_error(self):
        main.save("existing")
        with self.assertRaisesRegex(ToolError, "overwrite=true"):
            main.save("existing")

    def test_successful_architecture_commits_complete_document(self):
        result = main.draw_architecture("box: API, circle: Database")
        self.assertEqual(result["nodes"], 2)
        self.assertIsNone(result["url"])
        self.assertEqual(len(self.scene.all()), 5)
        self.assertEqual(self.scene.document()["files"], {})
        self.assertNotIn("custom", self.scene.document())

    def test_preview_is_explicitly_unavailable(self):
        with self.assertRaisesRegex(ToolError, "Use save"):
            main.preview()
        self.assertEqual(self.scene.document(), self.original)

    def test_state_replacement_is_validated_and_detached(self):
        with self.assertRaises(SceneError):
            self.scene.replace(new_document([{}]))
        self.assertEqual(self.scene.document(), self.original)
        snapshot = self.scene.document()
        snapshot["appState"].clear()
        self.original["files"].clear()
        self.assertTrue(self.scene.document()["appState"])
        self.assertTrue(self.scene.document()["files"])


if __name__ == "__main__":
    unittest.main()
