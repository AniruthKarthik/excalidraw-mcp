"""Deterministic layouts for the supported node subset."""

import math
import textwrap
from collections import defaultdict, deque

from excalidraw_mcp.errors import SceneError


def wrap_label(label: str, max_chars: int = 24) -> str:
    lines = []
    for paragraph in label.splitlines() or [""]:
        lines.extend(
            textwrap.wrap(paragraph, width=max_chars, break_long_words=True) or [""]
        )
    return "\n".join(lines)


def shape_dimensions(shape: str, label: str):
    lines = wrap_label(label).splitlines() or [""]
    text_width, text_height = max(map(len, lines)) * 12, len(lines) * 25
    if shape == "ellipse":
        size = max(140, text_width + 70, text_height + 70)
        return size, size
    if shape == "diamond":
        return max(180, text_width + 100), max(130, text_height + 70)
    return max(180, text_width + 60), max(100, text_height + 50)


def linear_layout(nodes, direction="horizontal", start_x=100, start_y=100, gap=100):
    if direction not in ("horizontal", "vertical"):
        raise SceneError("Layout direction must be horizontal or vertical")
    positioned, cursor = [], 0
    for node in nodes:
        width, height = shape_dimensions(node["shape"], node["label"])
        item = {
            **node,
            "label": wrap_label(node["label"]),
            "x": start_x,
            "y": start_y,
            "w": width,
            "h": height,
        }
        item["x" if direction == "horizontal" else "y"] += cursor
        positioned.append(item)
        cursor += (width if direction == "horizontal" else height) + gap
    return positioned


def horizontal_layout(nodes):
    return linear_layout(nodes)


def layered_layout(
    nodes,
    edges,
    direction="horizontal",
    start_x=100,
    start_y=100,
    rank_gap=180,
    node_gap=80,
):
    if direction not in ("horizontal", "vertical"):
        raise SceneError("Layout direction must be horizontal or vertical")
    ids = [node["id"] for node in nodes]
    incoming = {node_id: 0 for node_id in ids}
    outgoing = defaultdict(list)
    for edge in edges:
        outgoing[edge["source"]].append(edge["target"])
        incoming[edge["target"]] += 1
    queue = deque(node_id for node_id in ids if incoming[node_id] == 0)
    rank = {node_id: 0 for node_id in queue}
    visited = []
    while queue:
        current = queue.popleft()
        visited.append(current)
        for target in outgoing[current]:
            rank[target] = max(rank.get(target, 0), rank[current] + 1)
            incoming[target] -= 1
            if incoming[target] == 0:
                queue.append(target)
    if len(visited) != len(ids):
        raise SceneError("Layered layout requires an acyclic graph")
    groups, lookup = defaultdict(list), {node["id"]: node for node in nodes}
    for node_id in ids:
        groups[rank.get(node_id, 0)].append(lookup[node_id])
    sizes = {
        node_id: shape_dimensions(lookup[node_id]["shape"], lookup[node_id]["label"])
        for node_id in ids
    }
    offsets, cursor = {}, 0
    for level in sorted(groups):
        offsets[level] = cursor
        cursor += (
            max(
                sizes[n["id"]][0 if direction == "horizontal" else 1]
                for n in groups[level]
            )
            + rank_gap
        )
    positioned = []
    for level in sorted(groups):
        cross = 0
        for node in groups[level]:
            width, height = sizes[node["id"]]
            x = start_x + (offsets[level] if direction == "horizontal" else cross)
            y = start_y + (cross if direction == "horizontal" else offsets[level])
            positioned.append(
                {
                    **node,
                    "label": wrap_label(node["label"]),
                    "x": x,
                    "y": y,
                    "w": width,
                    "h": height,
                }
            )
            cross += (height if direction == "horizontal" else width) + node_gap
    return positioned


def boundary_point(node, target, coincident_direction=1):
    cx, cy = node["x"] + node["w"] / 2, node["y"] + node["h"] / 2
    tx, ty = target["x"] + target["w"] / 2, target["y"] + target["h"] / 2
    dx, dy = tx - cx, ty - cy
    if dx == dy == 0:
        dx = 1 if coincident_direction >= 0 else -1
    angle = node.get("angle", 0)
    cosine, sine = math.cos(angle), math.sin(angle)
    local_dx = dx * cosine + dy * sine
    local_dy = -dx * sine + dy * cosine
    half_width, half_height = node["w"] / 2, node["h"] / 2
    if node["shape"] == "ellipse":
        scale = 1 / math.sqrt(
            (local_dx / half_width) ** 2 + (local_dy / half_height) ** 2
        )
    elif node["shape"] == "diamond":
        scale = 1 / (
            abs(local_dx) / half_width + abs(local_dy) / half_height
        )
    else:
        scale = min(
            half_width / abs(local_dx) if local_dx else math.inf,
            half_height / abs(local_dy) if local_dy else math.inf,
        )
    local_x, local_y = local_dx * scale, local_dy * scale
    return (
        cx + local_x * cosine - local_y * sine,
        cy + local_x * sine + local_y * cosine,
    )
