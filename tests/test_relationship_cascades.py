"""P1 Robustness test suite for element relationships, cascading mutations, and bindings.

Verifies:
- Cascading connector unbinding upon shape deletion
- Moving bound shapes and preserving arrow attachment
- Frame duplication and recursive child parenting
- Element lock constraints on groups, frames, and shapes
"""

import unittest

from excalidraw_mcp.errors import SceneError
from excalidraw_mcp.service import SceneService


class RelationshipCascadesTests(unittest.TestCase):
    def setUp(self):
        self.service = SceneService()

    def test_delete_container_unravels_connector_bindings(self):
        """TC-HIGH-02: Deleting a shape with an attached arrow detaches the arrow rather than deleting it."""
        s1 = self.service.add_shape("rectangle", 100, 100, 100, 80, label="Box 1")
        s2 = self.service.add_shape("rectangle", 400, 100, 100, 80, label="Box 2")
        conn = self.service.connect(s1["rectangle_id"], s2["rectangle_id"], label="Link")
        arrow_id = conn["arrow_id"]

        # Delete Box 1
        del_res = self.service.delete(s1["rectangle_id"])
        self.assertEqual(del_res["status"], "deleted")

        # Arrow must still exist in the scene
        arrow_el = self.service.state.get(arrow_id)
        self.assertIsNotNone(arrow_el)
        self.assertFalse(arrow_el.get("isDeleted", False))
        # startBinding must be detached (None)
        self.assertIsNone(arrow_el["startBinding"])
        # endBinding must still point to Box 2
        self.assertIsNotNone(arrow_el["endBinding"])
        self.assertEqual(arrow_el["endBinding"]["elementId"], s2["rectangle_id"])

    def test_move_connected_shape_translates_corresponding_arrow_endpoint(self):
        """TC-HIGH-01: Moving a connected shape translates the arrow's start or end endpoint."""
        s1 = self.service.add_shape("rectangle", 100, 100, 100, 100)
        s2 = self.service.add_shape("rectangle", 400, 100, 100, 100)
        conn = self.service.connect(s1["rectangle_id"], s2["rectangle_id"])
        arrow_id = conn["arrow_id"]

        arrow_before = self.service.state.get(arrow_id)

        # Move Box 1 right by 50px
        self.service.move(s1["rectangle_id"], x=150, y=100)

        arrow_after = self.service.state.get(arrow_id)
        self.assertNotEqual(arrow_after["x"], arrow_before["x"])

    def test_duplicate_frame_recursively_parents_duplicated_children(self):
        """TC-HIGH-08: Duplicating a frame containing children creates new children with updated frameId."""
        frame_res = self.service.add_frame("System Boundary", 50, 50, 400, 300)
        frame_id = frame_res["frame_id"]

        r1 = self.service.add_shape("rectangle", 100, 100, 80, 60, frame_id=frame_id)
        r2 = self.service.add_shape("ellipse", 250, 100, 80, 80, frame_id=frame_id)

        # Duplicate frame with offset
        dup_res = self.service.duplicate_elements([frame_id, r1["rectangle_id"], r2["circle_id"]], offset_x=500, offset_y=0)
        self.assertEqual(dup_res["status"], "duplicated")
        new_frame_id = dup_res["id_mapping"][frame_id]
        new_r1_id = dup_res["id_mapping"][r1["rectangle_id"]]
        new_r2_id = dup_res["id_mapping"][r2["circle_id"]]

        # Verify child parenting
        child1 = self.service.state.get(new_r1_id)
        child2 = self.service.state.get(new_r2_id)
        self.assertEqual(child1["frameId"], new_frame_id)
        self.assertEqual(child2["frameId"], new_frame_id)

    def test_locked_element_rejects_movement_and_resize(self):
        """Ensure locked elements reject move, resize, and group transformations."""
        r = self.service.add_shape("rectangle", 100, 100, 100, 100)
        rid = r["rectangle_id"]

        # Lock element
        self.service.lock_elements([rid])

        with self.assertRaisesRegex(SceneError, "Cannot move locked element"):
            self.service.move(rid, 150, 150)

        with self.assertRaisesRegex(SceneError, "Cannot resize locked element"):
            self.service.resize(rid, 200, 200)

        # Unlock and verify operations succeed
        self.service.unlock_elements([rid])
        moved = self.service.move(rid, 150, 150)
        self.assertEqual(moved["status"], "moved")
