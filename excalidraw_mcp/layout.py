"""Deterministic layouts for the supported node subset."""

import math
import textwrap
from collections import defaultdict, deque

from excalidraw_mcp.errors import SceneError


def wrap_label(label: str, max_chars: int = 24) -> str:
    cleaned = label.replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for paragraph in cleaned.splitlines() or [""]:
        lines.extend(
            textwrap.wrap(paragraph, width=max_chars, break_long_words=True) or [""]
        )
    return "\n".join(lines)


def wrap_text_to_shape(
    label: str,
    shape: str = "rectangle",
    target_w: float | None = None,
    font_size: int = 20,
    font_family: str | int | None = None,
) -> str:
    """Intelligently wrap label text to fit within a shape's inscribed geometry."""
    if not label:
        return ""
    font_size = font_size or 20
    if target_w is not None and target_w > 0:
        if shape == "ellipse":
            # Inscribed rectangle inside ellipse: width * (1 / sqrt(2)) ~ 0.707 * width
            safe_w = max(60.0, (target_w * 0.707) - 32.0)
        elif shape == "diamond":
            # Inscribed rhombus: safe width at ~middle height is ~0.55 * width
            safe_w = max(60.0, (target_w * 0.55) - 32.0)
        else:
            # Rectangle: width minus horizontal padding (20px each side)
            safe_w = max(60.0, target_w - 40.0)
    else:
        if shape == "ellipse":
            safe_w = 140.0
        elif shape == "diamond":
            safe_w = 130.0
        else:
            safe_w = 180.0

    from .fonts import get_font
    try:
        font = get_font(font_family, font_size)
        bbox = font.getbbox("M")
        char_w = max(7.0, float(bbox[2] - bbox[0]) * 0.85)
    except Exception:
        char_w = max(7.0, float(font_size) * 0.55)

    max_chars = max(20, int(safe_w / char_w))
    return wrap_label(label, max_chars=max_chars)


def shape_dimensions(
    shape: str,
    label: str,
    font_size: int = 20,
    font_family: str | int | None = None,
) -> tuple[float, float]:
    """Calculate the bounding box dimensions of a shape required to enclose its text.

    Guarantees that all text lines fit inside with consistent internal padding,
    accounting for geometric boundaries of rectangles, ellipses, and diamonds.
    """
    from .fonts import measure_text_dimensions

    font_size = font_size or 20
    # Auto-wrap label according to shape geometry
    wrapped = wrap_text_to_shape(
        label, shape=shape, font_size=font_size, font_family=font_family
    )
    text_w, text_h, _ = measure_text_dimensions(
        wrapped, font_family=font_family, font_size=font_size
    )

    if shape == "ellipse":
        # For a circle/ellipse, diameter >= hypot(text_w, text_h) + 2 * padding
        diag = math.hypot(text_w, text_h)
        size = max(140.0, diag + 48.0)
        return size, size

    if shape == "diamond":
        # For a diamond (rhombus), corner fits inside: W_t/W + H_t/H <= 1.0
        min_w = text_w * 1.65 + 60.0
        min_h = text_h * 1.65 + 50.0
        return max(180.0, min_w), max(130.0, min_h)

    # Rectangle: text width + padding on left/right, text height + padding on top/bottom
    min_w = text_w + 48.0
    min_h = text_h + 36.0
    return max(180.0, min_w), max(100.0, min_h)


def linear_layout(nodes, direction="horizontal", start_x=100, start_y=100, gap=100):
    if direction not in ("horizontal", "vertical"):
        raise SceneError("Layout direction must be horizontal or vertical")
    if not nodes:
        return []
    dims = [
        shape_dimensions(
            n["shape"],
            n["label"],
            font_size=n.get("fontSize") or n.get("font_size") or 20,
            font_family=n.get("fontFamily") or n.get("font_family"),
        )
        for n in nodes
    ]
    max_cross = (
        max(h for w, h in dims) if direction == "horizontal" else max(w for w, h in dims)
    )
    positioned, cursor = [], 0
    for i, node in enumerate(nodes):
        width, height = dims[i]
        if direction == "horizontal":
            x = start_x + cursor
            y = start_y + (max_cross - height) / 2.0
            cursor += width + gap
        else:
            x = start_x + (max_cross - width) / 2.0
            y = start_y + cursor
            cursor += height + gap
        fs = node.get("fontSize") or node.get("font_size") or 20
        ff = node.get("fontFamily") or node.get("font_family")
        item = {
            **node,
            "label": wrap_text_to_shape(
                node["label"],
                shape=node["shape"],
                target_w=width,
                font_size=fs,
                font_family=ff,
            ),
            "x": x,
            "y": y,
            "w": width,
            "h": height,
        }
        positioned.append(item)
    return positioned


def grid_layout(
    nodes,
    cols=4,
    start_x=100,
    start_y=100,
    col_gap=60,
    row_gap=80,
    snake=True,
):
    """Layout nodes in a multi-row grid with snake routing for balanced aspect ratios."""
    if not nodes:
        return []
    dims = [
        shape_dimensions(
            n["shape"],
            n["label"],
            font_size=n.get("fontSize") or n.get("font_size") or 20,
            font_family=n.get("fontFamily") or n.get("font_family"),
        )
        for n in nodes
    ]
    cell_w = max(w for w, h in dims) + col_gap
    cell_h = max(h for w, h in dims) + row_gap

    positioned = []
    for i, node in enumerate(nodes):
        row = i // cols
        col_in_row = i % cols
        if snake and (row % 2 == 1):
            col = (cols - 1) - col_in_row
        else:
            col = col_in_row

        w, h = dims[i]
        x = start_x + col * cell_w + (cell_w - col_gap - w) / 2.0
        y = start_y + row * cell_h + (cell_h - row_gap - h) / 2.0
        fs = node.get("fontSize") or node.get("font_size") or 20
        ff = node.get("fontFamily") or node.get("font_family")
        positioned.append(
            {
                **node,
                "label": wrap_text_to_shape(
                    node["label"],
                    shape=node["shape"],
                    target_w=w,
                    font_size=fs,
                    font_family=ff,
                ),
                "x": x,
                "y": y,
                "w": w,
                "h": h,
            }
        )
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
        raise SceneError(
            "Layered layout requires an acyclic graph. Use layout='horizontal' or 'vertical' for cyclic graphs."
        )
    groups, lookup = defaultdict(list), {node["id"]: node for node in nodes}
    for node_id in ids:
        groups[rank.get(node_id, 0)].append(lookup[node_id])
    sizes = {
        node_id: shape_dimensions(
            lookup[node_id]["shape"],
            lookup[node_id]["label"],
            font_size=lookup[node_id].get("fontSize") or lookup[node_id].get("font_size") or 20,
            font_family=lookup[node_id].get("fontFamily") or lookup[node_id].get("font_family"),
        )
        for node_id in ids
    }

    # Calculate dynamic inter-rank gap to accommodate long edge labels without overlap
    rank_by_id = {node["id"]: rank.get(node["id"], 0) for node in nodes}
    inter_rank_gaps = {}
    sorted_levels = sorted(groups)
    for i, level in enumerate(sorted_levels[:-1]):
        next_level = sorted_levels[i + 1]
        spanning_edges = [
            e
            for e in edges
            if (
                rank_by_id.get(e["source"]) == level
                and rank_by_id.get(e["target"]) >= next_level
            )
            or (
                rank_by_id.get(e["target"]) == level
                and rank_by_id.get(e["source"]) >= next_level
            )
        ]
        max_lbl_len = 0
        for e in spanning_edges:
            lbl = e.get("label") or ""
            if lbl:
                max_lbl_len = max(
                    max_lbl_len, max(len(line) for line in lbl.splitlines())
                )

        if direction == "horizontal":
            needed_gap = max_lbl_len * 9 + 50 if max_lbl_len > 0 else rank_gap
        else:
            needed_gap = max_lbl_len * 4 + 40 if max_lbl_len > 0 else rank_gap
        inter_rank_gaps[level] = max(rank_gap, needed_gap)

    offsets, cursor = {}, 0
    for level in sorted_levels:
        offsets[level] = cursor
        rg = inter_rank_gaps.get(level, rank_gap)
        cursor += (
            max(
                sizes[n["id"]][0 if direction == "horizontal" else 1]
                for n in groups[level]
            )
            + rg
        )
    cross_dim = 1 if direction == "horizontal" else 0
    rank_cross_spans = {}
    for level in sorted(groups):
        level_nodes = groups[level]
        total_span = (
            sum(sizes[n["id"]][cross_dim] for n in level_nodes)
            + max(0, len(level_nodes) - 1) * node_gap
        )
        rank_cross_spans[level] = total_span

    max_cross_span = max(rank_cross_spans.values()) if rank_cross_spans else 0

    positioned = []
    for level in sorted(groups):
        cross = (max_cross_span - rank_cross_spans[level]) / 2.0
        rank_primary_max = max(
            sizes[n["id"]][0 if direction == "horizontal" else 1]
            for n in groups[level]
        )
        for node in groups[level]:
            width, height = sizes[node["id"]]
            node_primary = width if direction == "horizontal" else height
            primary_offset = offsets[level] + (rank_primary_max - node_primary) / 2.0
            x = start_x + (primary_offset if direction == "horizontal" else cross)
            y = start_y + (cross if direction == "horizontal" else primary_offset)
            fs = node.get("fontSize") or node.get("font_size") or 20
            ff = node.get("fontFamily") or node.get("font_family")
            positioned.append(
                {
                    **node,
                    "label": wrap_text_to_shape(
                        node["label"],
                        shape=node["shape"],
                        target_w=width,
                        font_size=fs,
                        font_family=ff,
                    ),
                    "x": x,
                    "y": y,
                    "w": width,
                    "h": height,
                }
            )
            cross += (height if direction == "horizontal" else width) + node_gap
    return positioned


def clustered_layout(
    nodes,
    edges,
    clusters,
    layout="layered",
    direction="horizontal",
    start_x=100,
    start_y=100,
    rank_gap=180,
    node_gap=80,
    cluster_padding=40,
    cluster_gap=80,
):
    """Layout nodes grouped by clusters, wrapping each cluster in a frame."""
    if direction not in ("horizontal", "vertical"):
        raise SceneError("Layout direction must be horizontal or vertical")

    cluster_lookup = {c["id"]: c.get("label", c["id"]) for c in clusters}
    cluster_order = [c["id"] for c in clusters]

    for node in nodes:
        cid = node.get("cluster")
        if cid and cid not in cluster_lookup:
            raise SceneError(f"Unknown cluster '{cid}' on node '{node['id']}'")

    positioned_nodes = []
    frames = []

    cursor_x, cursor_y = start_x, start_y

    for cid in cluster_order:
        c_label = cluster_lookup[cid]
        c_nodes = [node for node in nodes if node.get("cluster") == cid]
        if not c_nodes:
            fw, fh = 240, 160
            frames.append(
                {
                    "id": cid,
                    "name": c_label,
                    "x": cursor_x,
                    "y": cursor_y,
                    "w": fw,
                    "h": fh,
                }
            )
            if direction == "horizontal":
                cursor_x += fw + cluster_gap
            else:
                cursor_y += fh + cluster_gap
            continue

        c_node_ids = {n["id"] for n in c_nodes}
        c_edges = [
            e
            for e in edges
            if e.get("source") in c_node_ids and e.get("target") in c_node_ids
        ]

        inner_start_x = cursor_x + cluster_padding
        inner_start_y = cursor_y + cluster_padding + 20

        if layout == "layered":
            try:
                c_pos = layered_layout(
                    c_nodes,
                    c_edges,
                    direction=direction,
                    start_x=inner_start_x,
                    start_y=inner_start_y,
                    rank_gap=rank_gap,
                    node_gap=node_gap,
                )
            except SceneError:
                c_pos = linear_layout(
                    c_nodes,
                    direction=direction,
                    start_x=inner_start_x,
                    start_y=inner_start_y,
                    gap=node_gap,
                )
        else:
            c_pos = linear_layout(
                c_nodes,
                direction=direction,
                start_x=inner_start_x,
                start_y=inner_start_y,
                gap=node_gap,
            )

        min_x = min(n["x"] for n in c_pos)
        min_y = min(n["y"] for n in c_pos)
        max_x = max(n["x"] + n["w"] for n in c_pos)
        max_y = max(n["y"] + n["h"] for n in c_pos)

        fw = (max_x - min_x) + (2 * cluster_padding)
        fh = (max_y - min_y) + (2 * cluster_padding + 20)
        fx = min_x - cluster_padding
        fy = min_y - (cluster_padding + 20)

        frames.append(
            {
                "id": cid,
                "name": c_label,
                "x": fx,
                "y": fy,
                "w": fw,
                "h": fh,
            }
        )

        for n in c_pos:
            positioned_nodes.append({**n, "frame_id": cid})

        if direction == "horizontal":
            cursor_x = fx + fw + cluster_gap
        else:
            cursor_y = fy + fh + cluster_gap

    unclustered = [node for node in nodes if not node.get("cluster")]
    if unclustered:
        unclustered_ids = {n["id"] for n in unclustered}
        u_edges = [
            e
            for e in edges
            if e.get("source") in unclustered_ids and e.get("target") in unclustered_ids
        ]
        if layout == "layered":
            try:
                u_pos = layered_layout(
                    unclustered,
                    u_edges,
                    direction=direction,
                    start_x=cursor_x,
                    start_y=cursor_y,
                    rank_gap=rank_gap,
                    node_gap=node_gap,
                )
            except SceneError:
                u_pos = linear_layout(
                    unclustered,
                    direction=direction,
                    start_x=cursor_x,
                    start_y=cursor_y,
                    gap=node_gap,
                )
        else:
            u_pos = linear_layout(
                unclustered,
                direction=direction,
                start_x=cursor_x,
                start_y=cursor_y,
                gap=node_gap,
            )
        for n in u_pos:
            positioned_nodes.append({**n, "frame_id": None})

    return positioned_nodes, frames


def boundary_point(node, target, coincident_direction=1):
    cx, cy = node["x"] + node["w"] / 2, node["y"] + node["h"] / 2
    tx, ty = target["x"] + target["w"] / 2, target["y"] + target["h"] / 2
    dx, dy = tx - cx, ty - cy
    if dx == dy == 0:
        dx = 1 if coincident_direction >= 0 else -1
    angle = node.get("angle") or 0
    cosine, sine = math.cos(angle), math.sin(angle)
    local_dx = dx * cosine + dy * sine
    local_dy = -dx * sine + dy * cosine
    half_width, half_height = max(node["w"] / 2, 0.5), max(node["h"] / 2, 0.5)
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
