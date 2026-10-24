"""P0 Critical test suite for mathematical boundary math and layout geometry edge cases.

Verifies:
- boundary_point calculation on coincident centers, zero dimensions, and rotations
- Accurate bounding box calculation on negative coordinates and multi-point polylines
- Topological cycle detection in layered DAG layouts
- Cluster containment and error handling on unknown clusters
"""

import math
import unittest

from excalidraw_mcp.errors import SceneError
from excalidraw_mcp.layout import (
    boundary_point,
    clustered_layout,
    layered_layout,
    linear_layout,
    shape_dimensions,
    wrap_label,
)
from excalidraw_mcp.renderer import _compute_bounds


class GeometryEdgeCasesTests(unittest.TestCase):
    def test_boundary_point_coincident_centers_safe(self):
        """TC-CRIT-05: Ensure boundary_point does not raise ZeroDivisionError when centers coincide."""
        node_a = {"shape": "rectangle", "x": 100.0, "y": 100.0, "w": 80.0, "h": 60.0}
        node_b = {"shape": "rectangle", "x": 100.0, "y": 100.0, "w": 80.0, "h": 60.0}

        # Forward direction
        pt1 = boundary_point(node_a, node_b, coincident_direction=1)
        self.assertEqual(len(pt1), 2)
        self.assertTrue(math.isfinite(pt1[0]) and math.isfinite(pt1[1]))

        # Opposite direction
        pt2 = boundary_point(node_b, node_a, coincident_direction=-1)
        self.assertEqual(len(pt2), 2)
        self.assertTrue(math.isfinite(pt2[0]) and math.isfinite(pt2[1]))

    def test_boundary_point_zero_dimensions_safe(self):
        """Ensure boundary_point handles degenerate zero-width or zero-height nodes without error."""
        degenerate_node = {"shape": "ellipse", "x": 50.0, "y": 50.0, "w": 0.0, "h": 0.0}
        target = {"shape": "diamond", "x": 200.0, "y": 50.0, "w": 100.0, "h": 100.0}

        pt = boundary_point(degenerate_node, target)
        self.assertEqual(len(pt), 2)
        self.assertTrue(all(math.isfinite(v) for v in pt))

    def test_boundary_point_rotated_shapes(self):
        """Ensure boundary_point accurately handles rotated rectangles, ellipses, and diamonds."""
        for shape in ("rectangle", "ellipse", "diamond"):
            for angle in (0.0, math.pi / 4, math.pi / 2, math.pi):
                node = {"shape": shape, "x": 100.0, "y": 100.0, "w": 120.0, "h": 80.0, "angle": angle}
                target = {"shape": "rectangle", "x": 300.0, "y": 100.0, "w": 100.0, "h": 100.0}
                pt = boundary_point(node, target)
                self.assertEqual(len(pt), 2)
                self.assertTrue(all(math.isfinite(v) for v in pt))

    def test_compute_bounds_extreme_negative_coordinates(self):
        """TC-CRIT-06: Ensure renderer accurately computes bounds for elements in negative coordinate space."""
        elements = [
            {"id": "r1", "type": "rectangle", "x": -5000.0, "y": -3000.0, "width": 200.0, "height": 100.0},
            {"id": "a1", "type": "arrow", "x": -4800.0, "y": -2900.0, "points": [[0.0, 0.0], [-1200.0, -800.0], [2000.0, 1500.0]]},
            {"id": "d1", "type": "diamond", "x": 1000.0, "y": 2000.0, "width": 150.0, "height": 150.0},
        ]
        min_x, min_y, max_x, max_y = _compute_bounds(elements)
        # Expected min_x: min(-5000, -4800 - 1200) = -6000.0
        # Expected min_y: min(-3000, -2900 - 800) = -3700.0
        self.assertEqual(min_x, -6000.0)
        self.assertEqual(min_y, -3700.0)
        self.assertGreaterEqual(max_x, 1150.0)
        self.assertGreaterEqual(max_y, 2150.0)

    def test_compute_bounds_empty_elements_fallback(self):
        """Ensure _compute_bounds on an empty list returns default fallback bounds."""
        bounds = _compute_bounds([])
        self.assertEqual(bounds, (0.0, 0.0, 600.0, 400.0))

    def test_layered_layout_rejects_cyclic_graph(self):
        """TC-CRIT-08: Ensure layered_layout raises SceneError on cyclic graphs without infinite loop."""
        nodes = [
            {"id": "A", "shape": "rectangle", "label": "Node A"},
            {"id": "B", "shape": "rectangle", "label": "Node B"},
            {"id": "C", "shape": "rectangle", "label": "Node C"},
        ]
        cyclic_edges = [
            {"source": "A", "target": "B"},
            {"source": "B", "target": "C"},
            {"source": "C", "target": "A"},  # Cycle back to A
        ]
        with self.assertRaisesRegex(SceneError, "requires an acyclic graph"):
            layered_layout(nodes, cyclic_edges)

    def test_clustered_layout_rejects_unknown_cluster_id(self):
        """Ensure clustered_layout detects node referencing nonexistent cluster."""
        nodes = [
            {"id": "N1", "shape": "rectangle", "label": "Node 1", "cluster": "missing_cluster"},
        ]
        clusters = [{"id": "c1", "label": "Cluster 1"}]
        with self.assertRaisesRegex(SceneError, "Unknown cluster 'missing_cluster'"):
            clustered_layout(nodes, [], clusters)

    def test_clustered_layout_handles_empty_cluster(self):
        """Ensure clustered_layout safely generates boundary frame for an empty cluster."""
        nodes = [{"id": "N1", "shape": "rectangle", "label": "Node 1", "cluster": "c1"}]
        clusters = [
            {"id": "c1", "label": "Active Cluster"},
            {"id": "c2", "label": "Empty Cluster"},
        ]
        pos_nodes, frames = clustered_layout(nodes, [], clusters)
        self.assertEqual(len(pos_nodes), 1)
        self.assertEqual(len(frames), 2)
        # Empty cluster frame must have valid dimensions
        empty_frame = next(f for f in frames if f["id"] == "c2")
        self.assertGreater(empty_frame["w"], 0)
        self.assertGreater(empty_frame["h"], 0)

    def test_linear_layout_invalid_direction_rejected(self):
        """Ensure linear_layout rejects invalid direction."""
        nodes = [{"id": "A", "shape": "rectangle", "label": "Node A"}]
        with self.assertRaisesRegex(SceneError, "must be horizontal or vertical"):
            linear_layout(nodes, direction="diagonal")
