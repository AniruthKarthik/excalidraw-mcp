import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from excalidraw.errors import SceneError
from excalidraw.service import SceneService
from excalidraw.state import SceneState


class EditingWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.state = SceneState(max_history=3)
        self.service = SceneService(self.state)

    def test_inspect_paginate_and_get(self):
        ids = [self.service.add_text(i, 0, str(i))["text_id"] for i in range(4)]
        page = self.service.get_scene(offset=1, limit=2)
        self.assertEqual((page["total"], page["has_more"]), (4, True))
        self.assertEqual([el["id"] for el in page["elements"]], ids[1:3])
        self.assertEqual(self.service.get_element(ids[2])["element"]["text"], "2")
        with self.assertRaises(SceneError):
            self.service.get_scene(limit=201)

    def test_update_label_styles_and_remove_label(self):
        result = self.service.add_shape("rectangle", 0, 0, 100, 100)
        updated = self.service.update_element(result["rectangle_id"], label="API",
                                              background_color="#ffeeaa", opacity=50)
        self.assertIsNotNone(updated["label_id"])
        shape = self.state.get(result["rectangle_id"])
        label = self.state.get(updated["label_id"])
        self.assertEqual((shape["backgroundColor"], shape["opacity"]), ("#ffeeaa", 50))
        self.assertEqual((label["x"] + label["width"] / 2,
                          label["y"] + label["height"] / 2), (50, 50))
        removed = self.service.update_element(result["rectangle_id"], label="")
        self.assertIsNone(removed["label_id"])
        self.assertIsNone(self.state.get(updated["label_id"]))

    def test_resize_recenters_label_and_reroutes_connector(self):
        a = self.service.add_shape("rectangle", 0, 0, 100, 100, "A")
        b = self.service.add_shape("rectangle", 300, 0, 100, 100, "B")
        edge = self.service.connect(a["rectangle_id"], b["rectangle_id"], "request")
        self.service.resize(a["rectangle_id"], 200, 160)
        shape, label = self.state.get(a["rectangle_id"]), self.state.get(a["label_id"])
        self.assertEqual((label["x"] + label["width"] / 2,
                          label["y"] + label["height"] / 2), (100, 80))
        connector = self.state.get(edge["arrow_id"])
        self.assertEqual((connector["x"], connector["y"]), (200, 68))
        self.assertEqual(connector["startBinding"]["elementId"], a["rectangle_id"])

    def test_connect_rejects_invalid_targets_without_partial_change(self):
        shape = self.service.add_shape("rectangle", 0, 0, 100, 100)
        standalone = self.service.add_text(200, 0, "text")
        before = self.state.document()
        with self.assertRaises(SceneError):
            self.service.connect(shape["rectangle_id"], standalone["text_id"])
        self.assertEqual(self.state.document(), before)

    def test_undo_is_bounded_and_failed_or_read_operations_add_no_history(self):
        ids = []
        for i in range(5):
            ids.append(self.service.add_text(i, 0, str(i))["text_id"])
        self.assertEqual(self.state.history_depth, 3)
        before = self.state.history_depth
        self.service.get_scene()
        with self.assertRaises(SceneError):
            self.service.delete("missing")
        self.assertEqual(self.state.history_depth, before)
        for remaining in (4, 3, 2):
            self.service.undo()
            self.assertEqual(len(self.state.all()), remaining)
        with self.assertRaisesRegex(SceneError, "Nothing"):
            self.service.undo()

    def test_saved_scene_listing_and_read_do_not_change_active_scene(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"EXCALIDRAW_SCENE_DIR": directory}
        ):
            self.service.add_text(0, 0, "one")
            self.service.save("zeta")
            self.service.save("alpha")
            before, revision = self.state.document(), self.state.revision
            self.assertEqual(self.service.list_saved_scenes()["scenes"], ["alpha", "zeta"])
            self.assertEqual(json.loads(self.service.read_saved_scene("alpha")), before)
            self.assertEqual(self.state.revision, revision)


if __name__ == "__main__":
    unittest.main()
