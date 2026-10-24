"""P0 Critical test suite for state rollback and storage failure recovery.

Verifies:
- Transactional rollback on mutation callback exceptions
- Atomic rollback of partial batch mutations
- Storage failure handling under ENOSPC (disk full) and corrupt files
- History byte limits and memory bounds under rapid mutation bursts
"""

import errno
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from excalidraw_mcp.errors import SceneError
from excalidraw_mcp.scene import load_scene, save_scene
from excalidraw_mcp.service import SceneService
from excalidraw_mcp.state import SceneState


class StateRollbackAndStorageFailureTests(unittest.TestCase):
    def setUp(self):
        self.service = SceneService()

    def test_apply_callback_exception_rolls_back_all_mutations(self):
        """TC-CRIT-01: Ensure apply() leaves state unchanged if callback raises an exception."""
        # Initial state has 1 shape
        self.service.add_shape("rectangle", 10, 10, 100, 100, label="Initial")
        initial_doc = self.service.state.document()
        initial_rev = self.service.state.revision
        initial_history_depth = self.service.state.history_depth

        def failing_mutation(document):
            document["elements"].append({"id": "corrupt-1", "type": "rectangle", "x": 0, "y": 0, "width": 50, "height": 50})
            document["elements"].append({"id": "corrupt-2", "type": "rectangle", "x": 50, "y": 50, "width": 50, "height": 50})
            raise RuntimeError("Intentional database or business logic explosion")

        with self.assertRaises(RuntimeError):
            self.service.state.apply(failing_mutation)

        # State must be 100% identical to before the call
        self.assertEqual(self.service.state.document(), initial_doc)
        self.assertEqual(self.service.state.revision, initial_rev)
        self.assertEqual(self.service.state.history_depth, initial_history_depth)

    def test_nested_scene_mutations_rejected(self):
        """Ensure attempting a nested state.apply() call raises SceneError."""
        def outer_mutation(document):
            # Attempting nested apply
            self.service.state.apply(lambda d: None)

        with self.assertRaisesRegex(SceneError, "Nested scene mutations are not supported"):
            self.service.state.apply(outer_mutation)

    def test_batch_mutate_rolls_back_completely_on_mid_sequence_failure(self):
        """TC-CRIT-02: 8 valid operations followed by a failing 9th op must roll back all 8 ops."""
        initial_doc = self.service.state.document()
        initial_rev = self.service.state.revision

        # Build 10 operations: 1-8 valid, 9 invalid
        ops = []
        for i in range(8):
            ops.append({
                "action": "add_rectangle",
                "client_id": f"rect_{i}",
                "x": i * 100,
                "y": 100,
                "width": 80,
                "height": 60,
                "label": f"Box {i}",
            })
        # Op 9 tries to resize a non-existent element
        ops.append({
            "action": "resize",
            "element_id": "non-existent-shape-id-9999",
            "width": 200,
            "height": 200,
        })
        ops.append({
            "action": "add_rectangle",
            "x": 900,
            "y": 100,
            "width": 80,
            "height": 60,
        })

        with self.assertRaisesRegex(SceneError, "not found"):
            self.service.batch_mutate(ops)

        # Zero elements should be created; state and revision must remain unchanged
        self.assertEqual(self.service.state.document(), initial_doc)
        self.assertEqual(self.service.state.revision, initial_rev)

    def test_save_scene_enospc_disk_full_handling(self):
        """TC-CRIT-03: Simulate ENOSPC during save_scene atomic write and verify graceful failure."""
        doc = self.service.state.document()
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("excalidraw_mcp.scene.scene_directory", return_value=Path(tmpdir)):
                # Mock os.replace to simulate disk full at final rename
                with patch("os.replace", side_effect=OSError(errno.ENOSPC, "No space left on device")):
                    with self.assertRaisesRegex(SceneError, "Could not save scene"):
                        save_scene("test_full_disk", doc, overwrite=True)

                # Ensure no corrupt scene file remains
                target_path = os.path.join(tmpdir, "test_full_disk.excalidraw")
                self.assertFalse(os.path.exists(target_path))

    def test_load_scene_corrupt_json_file_handled(self):
        """TC-CRIT-04: Ensure load_scene on corrupted JSON file raises SceneError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scene_path = os.path.join(tmpdir, "corrupt_diagram.excalidraw")
            with open(scene_path, "w") as f:
                f.write('{"type": "excalidraw", "elements": [')  # Malformed JSON

            with patch("excalidraw_mcp.scene.scene_directory", return_value=Path(tmpdir)):
                with self.assertRaisesRegex(SceneError, "not a valid UTF-8 JSON document"):
                    load_scene("corrupt_diagram")

    def test_load_scene_empty_file_handled(self):
        """Ensure load_scene on a 0-byte file raises SceneError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scene_path = os.path.join(tmpdir, "empty_diagram.excalidraw")
            with open(scene_path, "w") as f:
                f.write("")  # 0 bytes

            with patch("excalidraw_mcp.scene.scene_directory", return_value=Path(tmpdir)):
                with self.assertRaisesRegex(SceneError, "not a valid UTF-8 JSON document"):
                    load_scene("empty_diagram")

    def test_save_scene_rejects_overwrite_when_false(self):
        """Ensure save_scene rejects overwriting existing file when overwrite=False."""
        doc = self.service.state.document()
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("excalidraw_mcp.scene.scene_directory", return_value=Path(tmpdir)):
                save_scene("existing_scene", doc, overwrite=False)
                with self.assertRaisesRegex(SceneError, "already exists"):
                    save_scene("existing_scene", doc, overwrite=False)

    def test_state_history_memory_limit_eviction(self):
        """Ensure SceneState._remember evicts older snapshots when max_history_bytes is exceeded."""
        state = SceneState(max_history=50, max_history_size=5_000)
        # Add 30 elements in rapid succession
        for i in range(30):
            state.add({"id": f"elem_{i}", "type": "rectangle", "x": i * 10, "y": 0, "width": 50, "height": 50})

        # History bytes must strictly respect upper bound
        self.assertLessEqual(state._history_bytes, 5_000)
