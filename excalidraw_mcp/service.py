"""Scene operations independent of MCP transport and server globals."""

from excalidraw_mcp.config import max_export_bytes
from excalidraw_mcp.elements import arrow, bind_text, diamond, ellipse, frame, rect, text
from excalidraw_mcp.errors import SceneError
from excalidraw_mcp.document import serialize_document
from excalidraw_mcp.models import _finite_number, new_document
from excalidraw_mcp.scene import list_scenes, load_scene, save_scene
from excalidraw_mcp.state import SceneState
from excalidraw_mcp.layout import boundary_point, clustered_layout, layered_layout, linear_layout, wrap_label
from excalidraw_mcp.parser import parse_architecture

SHAPES = {"rectangle": rect, "ellipse": ellipse, "diamond": diamond}


def _serialize_for_export(document):
    payload = serialize_document(document)
    size_limit = max_export_bytes()
    if len(payload.encode("utf-8")) > size_limit:
        raise SceneError(f"Export exceeds the configured limit of {size_limit} bytes")
    return payload


def _shape_elements(shape, x, y, w, h, label, style, frame_id=None):
    shape_el = SHAPES[shape](x, y, w, h, **style)
    if frame_id:
        shape_el["frameId"] = frame_id
    elements = [shape_el]
    if label:
        label_style = {
            k: v for k, v in style.items() if k in ("strokeColor", "opacity")
        }
        label_el = text(x, y, label, **label_style)
        if frame_id:
            label_el["frameId"] = frame_id
        bind_text(label_el, shape_el)
        _center_label(label_el, shape_el)
        elements.append(label_el)
    return elements


def _active(document):
    return {el["id"]: el for el in document["elements"] if not el.get("isDeleted")}


def _require(index, element_id):
    if element_id not in index:
        raise SceneError(f"Element '{element_id}' not found")
    return index[element_id]


def _translate(el, dx, dy):
    el["x"] += dx
    el["y"] += dy


def _label_for(index, container_id):
    return next(
        (el for el in index.values() if el.get("containerId") == container_id), None
    )


def _center_label(label, container):
    if container["type"] == "arrow" and container.get("points"):
        first, last = container["points"][0], container["points"][-1]
        cx = container["x"] + (first[0] + last[0]) / 2
        cy = container["y"] + (first[1] + last[1]) / 2
    else:
        cx = container["x"] + container.get("width", 0) / 2
        cy = container["y"] + container.get("height", 0) / 2
    label["x"], label["y"] = cx - label["width"] / 2, cy - label["height"] / 2


def _as_layout_node(el):
    return {
        "id": el["id"],
        "shape": el["type"],
        "x": el["x"],
        "y": el["y"],
        "w": el["width"],
        "h": el["height"],
        "angle": el.get("angle", 0),
    }


def _reroute_connector(index, connector):
    if connector.get("elbowed") or connector.get("angle", 0):
        raise SceneError(
            "Resizing shapes attached to elbowed or rotated arrows is not supported yet"
        )
    start_id = (connector.get("startBinding") or {}).get("elementId")
    end_id = (connector.get("endBinding") or {}).get("elementId")
    if not start_id or not end_id or start_id not in index or end_id not in index:
        return
    source, target = index[start_id], index[end_id]
    start = boundary_point(_as_layout_node(source), _as_layout_node(target), 1)
    end = boundary_point(_as_layout_node(target), _as_layout_node(source), -1)
    connector["x"], connector["y"] = start
    connector["points"] = [[0, 0], [end[0] - start[0], end[1] - start[1]]]
    connector["width"], connector["height"] = (
        abs(end[0] - start[0]),
        abs(end[1] - start[1]),
    )
    label = _label_for(index, connector["id"])
    if label:
        _center_label(label, connector)


def _move_arrow_endpoints(el, dx, dy, start, end):
    if (not (start and end)) and (el.get("elbowed") or el.get("angle", 0)):
        raise SceneError(
            "Moving shapes attached to elbowed or rotated arrows is not supported yet"
        )
    world = [[el["x"] + p[0], el["y"] + p[1]] for p in el["points"]]
    if start and end:
        world = [[x + dx, y + dy] for x, y in world]
    else:
        if start:
            world[0][0] += dx
            world[0][1] += dy
        if end:
            world[-1][0] += dx
            world[-1][1] += dy
    el["x"], el["y"] = world[0]
    el["points"] = [[x - el["x"], y - el["y"]] for x, y in world]
    el["width"] = max(p[0] for p in world) - min(p[0] for p in world)
    el["height"] = max(p[1] for p in world) - min(p[1] for p in world)


class SceneService:
    def __init__(self, state: SceneState | None = None):
        self.state = state if state is not None else SceneState()

    def add_shape(self, shape, x, y, w, h, label="", frame_id=None, **style):
        if shape not in SHAPES:
            raise SceneError("Shape must be rectangle, ellipse or diamond")
        elements = _shape_elements(shape, x, y, w, h, label, style, frame_id=frame_id)
        ids = self.state.add_many(elements)
        key = {
            "rectangle": "rectangle_id",
            "ellipse": "circle_id",
            "diamond": "diamond_id",
        }[shape]
        return {key: ids[0], "label_id": ids[1] if len(ids) > 1 else None}

    def add_arrow(self, x, y, x2, y2, label="", elbowed=False, **style):
        arrow_el = arrow(x, y, x2, y2, elbowed=elbowed, **style)
        elements = [arrow_el]
        if label:
            label_el = text(x, y, label, fontSize=14, **style)
            bind_text(label_el, arrow_el)
            _center_label(label_el, arrow_el)
            elements.append(label_el)
        ids = self.state.add_many(elements)
        return {"arrow_id": ids[0], "label_id": ids[1] if len(ids) > 1 else None}

    def add_text(self, x, y, content, font_size=20, frame_id=None, **style):
        if not isinstance(content, str) or not content.strip():
            raise SceneError("Text content cannot be empty")
        if frame_id:
            style["frameId"] = frame_id
        element = text(x, y, content, fontSize=font_size, **style)
        return {"text_id": self.state.add(element)}

    def get_element(self, element_id):
        element, revision = self.state.get_with_revision(element_id)
        if element is None or element.get("isDeleted"):
            raise SceneError(f"Element '{element_id}' not found")
        return {"element": element, "revision": revision}

    def get_scene(self, offset=0, limit=50):
        if (
            type(offset) is not int
            or type(limit) is not int
            or offset < 0
            or not 1 <= limit <= 200
        ):
            raise SceneError(
                "offset must be nonnegative and limit must be between 1 and 200"
            )
        document, revision = self.state.snapshot()
        elements = [el for el in document["elements"] if not el.get("isDeleted")]
        return {
            "revision": revision,
            "total": len(elements),
            "offset": offset,
            "limit": limit,
            "elements": elements[offset : offset + limit],
            "has_more": offset + limit < len(elements),
        }

    def list_saved_scenes(self):
        scenes = list_scenes()
        return {"scenes": scenes, "count": len(scenes)}

    def clear(self):
        self.state.clear()
        return {"status": "scene cleared"}

    def undo(self):
        return self.state.undo()

    def delete(self, element_id):
        def remove(document):
            index = _active(document)
            _require(index, element_id)
            removed = {element_id}
            removed.update(
                el["id"] for el in index.values() if el.get("containerId") == element_id
            )
            document["elements"] = [
                el for el in document["elements"] if el["id"] not in removed
            ]
            for el in document["elements"]:
                if el.get("frameId") in removed:
                    el["frameId"] = None
                if el["type"] == "arrow" and not el.get("isDeleted"):
                    for end in ("startBinding", "endBinding"):
                        if (el.get(end) or {}).get("elementId") in removed:
                            el[end] = None
            return {
                "status": "deleted",
                "element_id": element_id,
                "deleted_ids": [key for key in index if key in removed],
            }

        return self.state.apply(remove)

    def move(self, element_id, x, y):
        if not _finite_number(x) or not _finite_number(y):
            raise SceneError("Move coordinates must be finite numbers")

        def move_elements(document):
            index = _active(document)
            el = _require(index, element_id)
            if el.get("containerId"):
                raise SceneError(
                    "Move the label's container instead of moving bound text independently"
                )
            dx, dy = x - el["x"], y - el["y"]
            if not dx and not dy:
                return {"status": "moved", "element_id": element_id, "x": x, "y": y}
            if el["type"] == "arrow" and el.get("elbowed"):
                raise SceneError("Moving elbowed arrows is not supported yet")
            _translate(el, dx, dy)
            moved_targets = {element_id}
            owned_labels = {
                label["containerId"]: label
                for label in index.values()
                if label.get("containerId")
            }
            if el["type"] == "frame":
                for child in index.values():
                    if child.get("frameId") == element_id:
                        _translate(child, dx, dy)
                        moved_targets.add(child["id"])
            for label in index.values():
                if label.get("containerId") in moved_targets:
                    _translate(label, dx, dy)
                    moved_targets.add(label["id"])
            if el["type"] == "arrow":
                # A coordinate move intentionally detaches the arrow from shapes.
                el["startBinding"] = None
                el["endBinding"] = None
            for connector in index.values():
                if connector["type"] != "arrow" or connector["id"] in moved_targets:
                    continue
                start = (connector.get("startBinding") or {}).get(
                    "elementId"
                ) in moved_targets
                end = (connector.get("endBinding") or {}).get(
                    "elementId"
                ) in moved_targets
                if start or end:
                    _move_arrow_endpoints(connector, dx, dy, start, end)
                    # Preserve the label's offset from the endpoint midpoint.
                    label = owned_labels.get(connector["id"])
                    if label:
                        _translate(
                            label,
                            dx * (int(start) + int(end)) / 2,
                            dy * (int(start) + int(end)) / 2,
                        )
            return {"status": "moved", "element_id": element_id, "x": x, "y": y}

        return self.state.apply(move_elements)

    def resize(self, element_id, width, height):
        if (
            not _finite_number(width)
            or not _finite_number(height)
            or width <= 0
            or height <= 0
        ):
            raise SceneError("width and height must be positive finite numbers")

        def resize_element(document):
            index = _active(document)
            el = _require(index, element_id)
            if el["type"] not in (*SHAPES, "frame"):
                raise SceneError(
                    "Only rectangle, ellipse and diamond elements can be resized"
                )
            el["width"], el["height"] = width, height
            label = _label_for(index, element_id)
            if label:
                _center_label(label, el)
            for connector in index.values():
                if connector["type"] == "arrow" and any(
                    (connector.get(end) or {}).get("elementId") == element_id
                    for end in ("startBinding", "endBinding")
                ):
                    _reroute_connector(index, connector)
            return {
                "status": "resized",
                "element_id": element_id,
                "width": width,
                "height": height,
            }

        return self.state.apply(resize_element)

    def update_element(
        self,
        element_id,
        label=None,
        stroke_color=None,
        background_color=None,
        fill_style=None,
        stroke_width=None,
        stroke_style=None,
        opacity=None,
        roughness=None,
        roundness=None,
        frame_id=None,
        elbowed=None,
    ):
        updates = {
            "strokeColor": stroke_color,
            "backgroundColor": background_color,
            "fillStyle": fill_style,
            "strokeWidth": stroke_width,
            "strokeStyle": stroke_style,
            "opacity": opacity,
            "roughness": roughness,
        }
        updates = {key: value for key, value in updates.items() if value is not None}
        if roundness is not None:
            if roundness == "adaptive":
                updates["roundness"] = {"type": 3}
            elif roundness == "round":
                updates["roundness"] = {"type": 2}
            elif roundness == "sharp":
                updates["roundness"] = None
            elif isinstance(roundness, dict):
                updates["roundness"] = roundness
        if elbowed is not None:
            updates["elbowed"] = bool(elbowed)
        if label is None and frame_id is None and not updates:
            raise SceneError("Provide a label or at least one style update")

        def update(document):
            index = _active(document)
            el = _require(index, element_id)

            if frame_id is not None:
                if frame_id == "":
                    el["frameId"] = None
                    lbl = _label_for(index, element_id)
                    if lbl:
                        lbl["frameId"] = None
                else:
                    _require(index, frame_id)
                    if index[frame_id]["type"] != "frame":
                        raise SceneError(f"Element '{frame_id}' is not a frame")
                    el["frameId"] = frame_id
                    lbl = _label_for(index, element_id)
                    if lbl:
                        lbl["frameId"] = frame_id

            if el["type"] == "frame" and label is not None:
                el["name"] = label
                el.update(updates)
                return {
                    "status": "updated",
                    "element_id": element_id,
                    "label_id": None,
                }
            elif el["type"] == "text":
                container_id = el.get("containerId")
                container = index.get(container_id) if container_id else None
                label_id = el["id"]
                if label is not None:
                    if not label:
                        if container is None:
                            raise SceneError(
                                "Standalone text cannot be empty; use delete instead"
                            )
                        document["elements"] = [
                            item
                            for item in document["elements"]
                            if item["id"] != el["id"]
                        ]
                        index.pop(el["id"], None)
                        return {
                            "status": "updated",
                            "element_id": element_id,
                            "label_id": None,
                        }
                    else:
                        el["text"] = el["originalText"] = label
                        el["width"] = (
                            max(map(len, label.split("\n"))) * el["fontSize"] * 0.6
                        )
                        el["height"] = (
                            len(label.split("\n"))
                            * el["fontSize"]
                            * el["lineHeight"]
                        )
                        if container:
                            _center_label(el, container)
                el.update(updates)
                return {
                    "status": "updated",
                    "element_id": element_id,
                    "label_id": label_id,
                }
            else:
                target = _label_for(index, element_id)
                label_id = target.get("id") if target else None
                if label is not None:
                    if target is None:
                        if label:
                            label_style = {
                                "strokeColor": updates.get(
                                    "strokeColor", el.get("strokeColor", "#1e1e1e")
                                ),
                                "opacity": updates.get("opacity", el.get("opacity", 100)),
                            }
                            font_size = 14 if el["type"] == "arrow" else 20
                            target = text(
                                el["x"],
                                el["y"],
                                label,
                                fontSize=font_size,
                                **label_style,
                            )
                            if el.get("frameId"):
                                target["frameId"] = el["frameId"]
                            bind_text(target, el)
                            _center_label(target, el)
                            document["elements"].append(target)
                            index[target["id"]] = target
                            label_id = target["id"]
                    elif not label:
                        document["elements"] = [
                            item
                            for item in document["elements"]
                            if item["id"] != target["id"]
                        ]
                        index.pop(target["id"], None)
                        label_id = None
                        target = None
                    else:
                        target["text"] = target["originalText"] = label
                        target["width"] = (
                            max(map(len, label.split("\n"))) * target["fontSize"] * 0.6
                        )
                        target["height"] = (
                            len(label.split("\n"))
                            * target["fontSize"]
                            * target["lineHeight"]
                        )
                        _center_label(target, el)
                el.update(updates)
                return {
                    "status": "updated",
                    "element_id": element_id,
                    "label_id": label_id,
                }

        return self.state.apply(update)

    def connect(self, source_id, target_id, label="", elbowed=False, **style):
        if source_id == target_id:
            raise SceneError("A connector requires two different elements")

        def add_connection(document):
            index = _active(document)
            source, target = _require(index, source_id), _require(index, target_id)
            if source["type"] not in SHAPES or target["type"] not in SHAPES:
                raise SceneError(
                    "Connectors can target rectangle, ellipse or diamond elements"
                )
            source_node = {
                "shape": source["type"],
                "x": source["x"],
                "y": source["y"],
                "w": source["width"],
                "h": source["height"],
                "angle": source.get("angle", 0),
            }
            target_node = {
                "shape": target["type"],
                "x": target["x"],
                "y": target["y"],
                "w": target["width"],
                "h": target["height"],
                "angle": target.get("angle", 0),
            }
            start, end = (
                boundary_point(source_node, target_node, 1),
                boundary_point(target_node, source_node, -1),
            )
            connector = arrow(*start, *end, elbowed=elbowed, **style)
            connector["startBinding"] = {
                "elementId": source_id,
                "focus": 0,
                "gap": 0,
                "fixedPoint": [0.5, 0.5],
                "mode": "inside",
            }
            connector["endBinding"] = {
                "elementId": target_id,
                "focus": 0,
                "gap": 0,
                "fixedPoint": [0.5, 0.5],
                "mode": "inside",
            }
            document["elements"].append(connector)
            label_id = None
            if label:
                label_el = text(
                    (start[0] + end[0]) / 2,
                    (start[1] + end[1]) / 2,
                    label,
                    fontSize=14,
                    **style,
                )
                bind_text(label_el, connector)
                _center_label(label_el, connector)
                document["elements"].append(label_el)
                label_id = label_el["id"]
            return {
                "arrow_id": connector["id"],
                "label_id": label_id,
                "source_id": source_id,
                "target_id": target_id,
            }

        return self.state.apply(add_connection)

    def save(self, name, overwrite=False):
        document = self.state.document()
        path = save_scene(name, document, overwrite=overwrite)
        return {"path": path, "elements": len(document["elements"]), "status": "saved"}

    def export_scene(self):
        """Export a detached snapshot without filesystem access."""
        return _serialize_for_export(self.state.document())

    def read_saved_scene(self, name):
        return _serialize_for_export(load_scene(name))

    def load(self, name):
        revision = self.state.revision
        document = load_scene(name)
        self.state.replace(document, expected_revision=revision)
        return {
            "loaded": len(document["elements"]),
            "name": name,
            "status": "scene loaded",
        }

    def preview(self, scale=1.0, padding=40):
        if not _finite_number(scale) or scale < 0.25 or scale > 4.0:
            raise SceneError("scale must be a finite number between 0.25 and 4.0")
        if (
            not isinstance(padding, int)
            or isinstance(padding, bool)
            or padding < 0
            or padding > 200
        ):
            raise SceneError("padding must be an integer between 0 and 200")
        document, _ = self.state.snapshot()
        from .renderer import render_scene_to_png

        return render_scene_to_png(document, scale=scale, padding=padding)

    def draw_architecture(self, prompt, **style):
        revision = self.state.revision
        nodes = parse_architecture(prompt)
        if not nodes or any(not node["label"].strip() for node in nodes):
            raise SceneError(
                "Provide at least one nonempty component label, e.g. 'box: API, box: Database'"
            )
        graph_nodes = [{**node, "id": node["id"]} for node in nodes]
        edges = [
            {
                "id": f"edge-{i}",
                "source": nodes[i - 1]["id"],
                "target": nodes[i]["id"],
                "label": "",
            }
            for i in range(1, len(nodes))
        ]
        result = self.draw_graph(
            graph_nodes,
            edges,
            layout="horizontal",
            style=style,
            expected_revision=revision,
        )
        return {
            **result,
            "url": None,
            "next_step": "Use save(name) or export_scene(), then import the document into Excalidraw.",
        }

    def add_frame(self, name, x, y, w, h, element_ids=None, **style):
        if (
            not _finite_number(x)
            or not _finite_number(y)
            or not _finite_number(w)
            or not _finite_number(h)
        ):
            raise SceneError("Frame coordinates and dimensions must be finite numbers")
        if w <= 0 or h <= 0:
            raise SceneError("Frame width and height must be positive")
        if not isinstance(name, str):
            raise SceneError("Frame name must be a string")

        def create_frame(document):
            index = _active(document)
            frame_el = frame(x, y, w, h, name=name, **style)
            if element_ids:
                for eid in element_ids:
                    target = _require(index, eid)
                    target["frameId"] = frame_el["id"]
                    lbl = _label_for(index, eid)
                    if lbl:
                        lbl["frameId"] = frame_el["id"]
            document["elements"].insert(0, frame_el)
            return {"frame_id": frame_el["id"]}

        return self.state.apply(create_frame)

    def find_elements(
        self,
        query=None,
        type=None,
        frame_id=None,
        element_id=None,
        connected_to=None,
        include_bound_labels=False,
        limit=50,
    ):
        if (
            limit is not None
            and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 1 or limit > 200)
        ):
            raise SceneError("limit must be an integer between 1 and 200")

        document, revision = self.state.snapshot()
        active = [el for el in document["elements"] if not el.get("isDeleted")]
        index = {el["id"]: el for el in active}

        connected_ids = set()
        if connected_to:
            if connected_to not in index:
                raise SceneError(f"Element '{connected_to}' not found")
            for el in active:
                if el["type"] == "arrow":
                    sb = (el.get("startBinding") or {}).get("elementId")
                    eb = (el.get("endBinding") or {}).get("elementId")
                    if sb == connected_to or eb == connected_to:
                        connected_ids.add(el["id"])
                        if sb and sb != connected_to:
                            connected_ids.add(sb)
                        if eb and eb != connected_to:
                            connected_ids.add(eb)

        matches = []
        q_lower = (
            query.strip().lower()
            if (isinstance(query, str) and query.strip())
            else None
        )

        for el in active:
            eid = el["id"]
            etype = el["type"]

            if not include_bound_labels and el.get("containerId") and element_id != eid:
                continue

            if element_id and eid != element_id:
                continue

            if type and etype != type:
                continue

            if frame_id is not None:
                if el.get("frameId") != frame_id:
                    continue

            if connected_to:
                if eid not in connected_ids:
                    continue

            label_el = _label_for(index, eid)
            label_text = (
                label_el.get("text")
                if label_el
                else (el.get("text") if etype == "text" else None)
            )
            frame_name = el.get("name") if etype == "frame" else None

            if q_lower:
                matched_query = False
                if label_text and q_lower in label_text.lower():
                    matched_query = True
                elif frame_name and q_lower in frame_name.lower():
                    matched_query = True
                elif q_lower in eid.lower():
                    matched_query = True
                if not matched_query:
                    continue

            bound_elements = el.get("boundElements") or []
            bound_ids = [
                b["id"]
                for b in bound_elements
                if isinstance(b, dict) and b.get("id")
            ]

            summary = {
                "id": eid,
                "type": etype,
                "x": float(el["x"]),
                "y": float(el["y"]),
                "width": float(el.get("width", 0)),
                "height": float(el.get("height", 0)),
                "bound_element_ids": bound_ids,
            }
            if label_text is not None:
                summary["label"] = label_text
            if frame_name is not None:
                summary["name"] = frame_name
            if el.get("frameId"):
                summary["frame_id"] = el["frameId"]
            if el.get("containerId"):
                summary["container_id"] = el["containerId"]
            if el.get("strokeColor"):
                summary["stroke_color"] = el["strokeColor"]
            if el.get("backgroundColor"):
                summary["background_color"] = el["backgroundColor"]

            matches.append(summary)

        return {
            "total": len(matches),
            "matches": matches[:limit],
            "revision": revision,
        }

    def batch_mutate(self, operations):
        if not isinstance(operations, list) or not operations:
            raise SceneError("Operations must be a non-empty list")
        if len(operations) > 500:
            raise SceneError("Batch is limited to 500 operations")

        def execute_batch(document):
            index = _active(document)
            ref_map = {}
            results = []

            def resolve(val):
                if isinstance(val, str):
                    return ref_map.get(val, val)
                return val

            def resolve_list(vals):
                if isinstance(vals, list):
                    return [ref_map.get(v, v) for v in vals]
                return vals

            for i, raw_op in enumerate(operations):
                op = raw_op if isinstance(raw_op, dict) else raw_op.model_dump()
                action = op.get("action")
                if not action:
                    raise SceneError(f"Operation at index {i} is missing 'action'")

                client_id = op.get("client_id")

                if action in ("add_rectangle", "add_circle", "add_diamond"):
                    shape = {
                        "add_rectangle": "rectangle",
                        "add_circle": "ellipse",
                        "add_diamond": "diamond",
                    }[action]
                    x = op.get("x")
                    y = op.get("y")
                    w = (
                        op.get("w")
                        if op.get("w") is not None
                        else op.get("width", op.get("size"))
                    )
                    h = (
                        op.get("h")
                        if op.get("h") is not None
                        else op.get("height", op.get("size"))
                    )
                    if shape == "ellipse" and op.get("size") is not None:
                        w = h = op.get("size")
                    if (
                        not _finite_number(x)
                        or not _finite_number(y)
                        or not _finite_number(w)
                        or not _finite_number(h)
                    ):
                        raise SceneError(
                            f"Operation {i} ({action}): coordinates and dimensions must be finite numbers"
                        )
                    if w <= 0 or h <= 0:
                        raise SceneError(
                            f"Operation {i} ({action}): dimensions must be positive"
                        )
                    style = {
                        k: v
                        for k, v in op.items()
                        if k
                        in (
                            "strokeColor",
                            "backgroundColor",
                            "fillStyle",
                            "strokeWidth",
                            "strokeStyle",
                            "opacity",
                            "roughness",
                            "roundness",
                        )
                        and v is not None
                    }
                    frame_id = resolve(op.get("frame_id"))
                    if frame_id:
                        _require(index, frame_id)
                    els = _shape_elements(
                        shape,
                        x,
                        y,
                        w,
                        h,
                        op.get("label", ""),
                        style,
                        frame_id=frame_id,
                    )
                    for el in els:
                        document["elements"].append(el)
                        index[el["id"]] = el
                    key = {
                        "rectangle": "rectangle_id",
                        "ellipse": "circle_id",
                        "diamond": "diamond_id",
                    }[shape]
                    res = {
                        "action": action,
                        key: els[0]["id"],
                        "label_id": els[1]["id"] if len(els) > 1 else None,
                    }
                    if client_id:
                        ref_map[client_id] = els[0]["id"]
                    results.append(res)

                elif action == "add_frame":
                    x = op.get("x")
                    y = op.get("y")
                    w = (
                        op.get("w")
                        if op.get("w") is not None
                        else op.get("width")
                    )
                    h = (
                        op.get("h")
                        if op.get("h") is not None
                        else op.get("height")
                    )
                    name = op.get("name", "")
                    if (
                        not _finite_number(x)
                        or not _finite_number(y)
                        or not _finite_number(w)
                        or not _finite_number(h)
                    ):
                        raise SceneError(
                            f"Operation {i} (add_frame): coordinates and dimensions must be finite numbers"
                        )
                    if w <= 0 or h <= 0:
                        raise SceneError(
                            f"Operation {i} (add_frame): width and height must be positive"
                        )
                    style = {
                        k: v
                        for k, v in op.items()
                        if k
                        in (
                            "strokeColor",
                            "backgroundColor",
                            "fillStyle",
                            "strokeWidth",
                            "strokeStyle",
                            "opacity",
                            "roughness",
                        )
                        and v is not None
                    }
                    frame_el = frame(x, y, w, h, name=name, **style)
                    eids = resolve_list(op.get("element_ids"))
                    if eids:
                        for eid in eids:
                            target = _require(index, eid)
                            target["frameId"] = frame_el["id"]
                            lbl = _label_for(index, eid)
                            if lbl:
                                lbl["frameId"] = frame_el["id"]
                    document["elements"].insert(0, frame_el)
                    index[frame_el["id"]] = frame_el
                    res = {"action": "add_frame", "frame_id": frame_el["id"]}
                    if client_id:
                        ref_map[client_id] = frame_el["id"]
                    results.append(res)

                elif action == "add_arrow":
                    x, y = op.get("x"), op.get("y")
                    x2, y2 = op.get("x2"), op.get("y2")
                    if not all(_finite_number(v) for v in (x, y, x2, y2)):
                        raise SceneError(
                            f"Operation {i} (add_arrow): points must be finite numbers"
                        )
                    elbowed = op.get("elbowed", False)
                    style = {
                        k: v
                        for k, v in op.items()
                        if k
                        in (
                            "strokeColor",
                            "strokeWidth",
                            "strokeStyle",
                            "opacity",
                            "roughness",
                        )
                        and v is not None
                    }
                    arrow_el = arrow(x, y, x2, y2, elbowed=elbowed, **style)
                    els = [arrow_el]
                    lbl_text = op.get("label", "")
                    if lbl_text:
                        lbl_el = text(x, y, lbl_text, fontSize=14, **style)
                        bind_text(lbl_el, arrow_el)
                        _center_label(lbl_el, arrow_el)
                        els.append(lbl_el)
                    for el in els:
                        document["elements"].append(el)
                        index[el["id"]] = el
                    res = {
                        "action": "add_arrow",
                        "arrow_id": arrow_el["id"],
                        "label_id": els[1]["id"] if len(els) > 1 else None,
                    }
                    if client_id:
                        ref_map[client_id] = arrow_el["id"]
                    results.append(res)

                elif action == "add_text":
                    x, y = op.get("x"), op.get("y")
                    content = op.get("content")
                    if not _finite_number(x) or not _finite_number(y):
                        raise SceneError(
                            f"Operation {i} (add_text): coordinates must be finite numbers"
                        )
                    if not isinstance(content, str) or not content.strip():
                        raise SceneError(
                            f"Operation {i} (add_text): content cannot be empty"
                        )
                    font_size = op.get("font_size", 20)
                    style = {
                        k: v
                        for k, v in op.items()
                        if k in ("strokeColor", "opacity") and v is not None
                    }
                    frame_id = resolve(op.get("frame_id"))
                    if frame_id:
                        _require(index, frame_id)
                        style["frameId"] = frame_id
                    txt_el = text(x, y, content, fontSize=font_size, **style)
                    document["elements"].append(txt_el)
                    index[txt_el["id"]] = txt_el
                    res = {"action": "add_text", "text_id": txt_el["id"]}
                    if client_id:
                        ref_map[client_id] = txt_el["id"]
                    results.append(res)

                elif action == "connect":
                    source_id = resolve(op.get("source_id"))
                    target_id = resolve(op.get("target_id"))
                    if not source_id or not target_id:
                        raise SceneError(
                            f"Operation {i} (connect): source_id and target_id are required"
                        )
                    if source_id == target_id:
                        raise SceneError(
                            f"Operation {i} (connect): source and target must differ"
                        )
                    source = _require(index, source_id)
                    target = _require(index, target_id)
                    if source["type"] not in SHAPES or target["type"] not in SHAPES:
                        raise SceneError(
                            f"Operation {i} (connect): connectors can target rectangle, ellipse or diamond elements"
                        )
                    source_node = {
                        "shape": source["type"],
                        "x": source["x"],
                        "y": source["y"],
                        "w": source["width"],
                        "h": source["height"],
                        "angle": source.get("angle", 0),
                    }
                    target_node = {
                        "shape": target["type"],
                        "x": target["x"],
                        "y": target["y"],
                        "w": target["width"],
                        "h": target["height"],
                        "angle": target.get("angle", 0),
                    }
                    start = boundary_point(source_node, target_node, 1)
                    end = boundary_point(target_node, source_node, -1)
                    elbowed = op.get("elbowed", False)
                    style = {
                        k: v
                        for k, v in op.items()
                        if k
                        in (
                            "strokeColor",
                            "strokeWidth",
                            "strokeStyle",
                            "opacity",
                            "roughness",
                        )
                        and v is not None
                    }
                    connector = arrow(*start, *end, elbowed=elbowed, **style)
                    connector["startBinding"] = {
                        "elementId": source_id,
                        "focus": 0,
                        "gap": 0,
                        "fixedPoint": [0.5, 0.5],
                        "mode": "inside",
                    }
                    connector["endBinding"] = {
                        "elementId": target_id,
                        "focus": 0,
                        "gap": 0,
                        "fixedPoint": [0.5, 0.5],
                        "mode": "inside",
                    }
                    document["elements"].append(connector)
                    index[connector["id"]] = connector
                    lbl_id = None
                    label = op.get("label", "")
                    if label:
                        label_el = text(
                            (start[0] + end[0]) / 2,
                            (start[1] + end[1]) / 2,
                            label,
                            fontSize=14,
                            **style,
                        )
                        bind_text(label_el, connector)
                        _center_label(label_el, connector)
                        document["elements"].append(label_el)
                        index[label_el["id"]] = label_el
                        lbl_id = label_el["id"]
                    res = {
                        "action": "connect",
                        "arrow_id": connector["id"],
                        "label_id": lbl_id,
                        "source_id": source_id,
                        "target_id": target_id,
                    }
                    if client_id:
                        ref_map[client_id] = connector["id"]
                    results.append(res)

                elif action == "move":
                    eid = resolve(op.get("element_id"))
                    x, y = op.get("x"), op.get("y")
                    if not eid or not _finite_number(x) or not _finite_number(y):
                        raise SceneError(
                            f"Operation {i} (move): element_id, finite x and y are required"
                        )
                    el = _require(index, eid)
                    if el.get("containerId"):
                        raise SceneError(
                            "Move the label's container instead of moving bound text independently"
                        )
                    dx, dy = x - el["x"], y - el["y"]
                    if dx or dy:
                        if el["type"] == "arrow" and el.get("elbowed"):
                            raise SceneError(
                                "Moving elbowed arrows is not supported yet"
                            )
                        _translate(el, dx, dy)
                        moved_targets = {eid}
                        owned_labels = {
                            lbl["containerId"]: lbl
                            for lbl in index.values()
                            if lbl.get("containerId")
                        }
                        if el["type"] == "frame":
                            for child in index.values():
                                if child.get("frameId") == eid:
                                    _translate(child, dx, dy)
                                    moved_targets.add(child["id"])
                        for lbl in index.values():
                            if lbl.get("containerId") in moved_targets:
                                _translate(lbl, dx, dy)
                                moved_targets.add(lbl["id"])
                        if el["type"] == "arrow":
                            el["startBinding"] = None
                            el["endBinding"] = None
                        for conn in index.values():
                            if conn["type"] != "arrow" or conn["id"] in moved_targets:
                                continue
                            start = (
                                (conn.get("startBinding") or {}).get("elementId")
                                in moved_targets
                            )
                            end = (
                                (conn.get("endBinding") or {}).get("elementId")
                                in moved_targets
                            )
                            if start or end:
                                _move_arrow_endpoints(conn, dx, dy, start, end)
                                lbl = owned_labels.get(conn["id"])
                                if lbl:
                                    _translate(
                                        lbl,
                                        dx * (int(start) + int(end)) / 2,
                                        dy * (int(start) + int(end)) / 2,
                                    )
                    results.append(
                        {
                            "action": "move",
                            "status": "moved",
                            "element_id": eid,
                            "x": x,
                            "y": y,
                        }
                    )

                elif action == "resize":
                    eid = resolve(op.get("element_id"))
                    w = (
                        op.get("w")
                        if op.get("w") is not None
                        else op.get("width")
                    )
                    h = (
                        op.get("h")
                        if op.get("h") is not None
                        else op.get("height")
                    )
                    if (
                        not eid
                        or not _finite_number(w)
                        or not _finite_number(h)
                        or w <= 0
                        or h <= 0
                    ):
                        raise SceneError(
                            f"Operation {i} (resize): element_id, positive width and height required"
                        )
                    el = _require(index, eid)
                    if el["type"] not in (*SHAPES, "frame"):
                        raise SceneError(
                            f"Operation {i} (resize): only rectangle, ellipse, diamond, frame can be resized"
                        )
                    el["width"], el["height"] = w, h
                    lbl = _label_for(index, eid)
                    if lbl:
                        _center_label(lbl, el)
                    for conn in index.values():
                        if conn["type"] == "arrow" and any(
                            (conn.get(end) or {}).get("elementId") == eid
                            for end in ("startBinding", "endBinding")
                        ):
                            _reroute_connector(index, conn)
                    results.append(
                        {
                            "action": "resize",
                            "status": "resized",
                            "element_id": eid,
                            "width": w,
                            "height": h,
                        }
                    )

                elif action == "update_element":
                    eid = resolve(op.get("element_id"))
                    if not eid:
                        raise SceneError(
                            f"Operation {i} (update_element): element_id is required"
                        )
                    el = _require(index, eid)
                    label = op.get("label")
                    style_keys = (
                        "strokeColor",
                        "backgroundColor",
                        "fillStyle",
                        "strokeWidth",
                        "strokeStyle",
                        "opacity",
                        "roughness",
                    )
                    updates = {
                        k: op[k] for k in style_keys if op.get(k) is not None
                    }
                    if op.get("roundness") is not None:
                        r = op["roundness"]
                        updates["roundness"] = (
                            {"type": 3}
                            if r == "adaptive"
                            else ({"type": 2} if r == "round" else None)
                        )
                    if op.get("elbowed") is not None:
                        updates["elbowed"] = bool(op["elbowed"])
                    target_frame_id = resolve(op.get("frame_id"))
                    if target_frame_id is not None:
                        if target_frame_id == "":
                            el["frameId"] = None
                            tgt_lbl = _label_for(index, eid)
                            if tgt_lbl:
                                tgt_lbl["frameId"] = None
                        else:
                            _require(index, target_frame_id)
                            el["frameId"] = target_frame_id
                            tgt_lbl = _label_for(index, eid)
                            if tgt_lbl:
                                tgt_lbl["frameId"] = target_frame_id
                    if el["type"] == "frame" and label is not None:
                        el["name"] = label
                    elif el["type"] == "text":
                        cid = el.get("containerId")
                        container = index.get(cid) if cid else None
                        if label is not None:
                            if not label:
                                if container is None:
                                    raise SceneError(
                                        "Standalone text cannot be empty; use delete instead"
                                    )
                                document["elements"] = [
                                    item
                                    for item in document["elements"]
                                    if item["id"] != el["id"]
                                ]
                                index.pop(el["id"], None)
                            else:
                                el["text"] = el["originalText"] = label
                                el["width"] = (
                                    max(map(len, label.split("\n")))
                                    * el["fontSize"]
                                    * 0.6
                                )
                                el["height"] = (
                                    len(label.split("\n"))
                                    * el["fontSize"]
                                    * el["lineHeight"]
                                )
                                if container:
                                    _center_label(el, container)
                        el.update(updates)
                    else:
                        target = _label_for(index, eid)
                        if label is not None:
                            if target is None and label:
                                lbl_style = {
                                    "strokeColor": updates.get(
                                        "strokeColor",
                                        el.get("strokeColor", "#1e1e1e"),
                                    ),
                                    "opacity": updates.get(
                                        "opacity", el.get("opacity", 100)
                                    ),
                                }
                                fs = 14 if el["type"] == "arrow" else 20
                                target = text(
                                    el["x"],
                                    el["y"],
                                    label,
                                    fontSize=fs,
                                    **lbl_style,
                                )
                                if el.get("frameId"):
                                    target["frameId"] = el["frameId"]
                                bind_text(target, el)
                                _center_label(target, el)
                                document["elements"].append(target)
                                index[target["id"]] = target
                            elif target is not None and not label:
                                document["elements"] = [
                                    item
                                    for item in document["elements"]
                                    if item["id"] != target["id"]
                                ]
                                index.pop(target["id"], None)
                            elif target is not None:
                                target["text"] = target["originalText"] = label
                                target["width"] = (
                                    max(map(len, label.split("\n")))
                                    * target["fontSize"]
                                    * 0.6
                                )
                                target["height"] = (
                                    len(label.split("\n"))
                                    * target["fontSize"]
                                    * target["lineHeight"]
                                )
                                _center_label(target, el)
                        el.update(updates)
                    results.append(
                        {
                            "action": "update_element",
                            "status": "updated",
                            "element_id": eid,
                        }
                    )

                elif action == "delete":
                    eid = resolve(op.get("element_id"))
                    if not eid:
                        raise SceneError(
                            f"Operation {i} (delete): element_id is required"
                        )
                    _require(index, eid)
                    removed = {eid}
                    removed.update(
                        el["id"]
                        for el in index.values()
                        if el.get("containerId") == eid
                    )
                    document["elements"] = [
                        el
                        for el in document["elements"]
                        if el["id"] not in removed
                    ]
                    for el in document["elements"]:
                        if el.get("frameId") == eid:
                            el["frameId"] = None
                        if el["type"] == "arrow" and not el.get("isDeleted"):
                            for end in ("startBinding", "endBinding"):
                                if (el.get(end) or {}).get("elementId") in removed:
                                    el[end] = None
                    for r in removed:
                        index.pop(r, None)
                    results.append(
                        {
                            "action": "delete",
                            "status": "deleted",
                            "element_id": eid,
                        }
                    )

                else:
                    raise SceneError(f"Unknown action '{action}' at operation {i}")

            return {
                "status": "batch executed",
                "operations_executed": len(results),
                "results": results,
                "ref_map": ref_map,
            }

        result = self.state.apply(execute_batch)
        return {**result, "revision": self.state.revision}

    def draw_graph(
        self,
        nodes,
        edges,
        clusters=None,
        layout="layered",
        direction="horizontal",
        elbowed=False,
        roundness=None,
        style=None,
        expected_revision=None,
    ):
        style = dict(style or {})
        if roundness is not None:
            style["roundness"] = roundness
        revision = (
            self.state.revision if expected_revision is None else expected_revision
        )
        if not isinstance(nodes, list) or not nodes:
            raise SceneError("Graph requires at least one node")
        if not isinstance(edges, list):
            raise SceneError("Graph edges must be a list")
        if len(nodes) > 200 or len(edges) > 500:
            raise SceneError("Graph is limited to 200 nodes and 500 edges")
        normalized_nodes = []
        for node in nodes:
            if not isinstance(node, dict):
                raise SceneError("Each graph node must be an object")
            if (
                not isinstance(node.get("id"), str)
                or not isinstance(node.get("label"), str)
                or not node["id"].strip()
                or not node["label"].strip()
                or len(node["id"]) > 200
                or len(node["label"]) > 2000
                or node.get("shape", "rectangle") not in SHAPES
            ):
                raise SceneError(
                    "Each graph node needs a unique ID, label and supported shape"
                )
            n_data = {**node, "shape": node.get("shape", "rectangle")}
            if "cluster" in node and node["cluster"] is not None:
                if not isinstance(node["cluster"], str) or not node["cluster"].strip():
                    raise SceneError(f"Node '{node['id']}' has invalid cluster ID")
                n_data["cluster"] = node["cluster"]
            normalized_nodes.append(n_data)

        node_ids = [node["id"] for node in normalized_nodes]
        if len(node_ids) != len(set(node_ids)):
            raise SceneError("Graph node IDs must be unique")
        allowed = set(node_ids)

        explicit_edge_ids = set()
        for edge in edges:
            if not isinstance(edge, dict):
                raise SceneError("Each graph edge must be an object")
            edge_id = edge.get("id")
            if edge_id is None:
                continue
            if (
                not isinstance(edge_id, str)
                or not edge_id.strip()
                or len(edge_id) > 200
                or edge_id in explicit_edge_ids
            ):
                raise SceneError("Graph edges need unique nonempty IDs")
            explicit_edge_ids.add(edge_id)

        edge_ids = set(explicit_edge_ids)
        normalized_edges = []
        generated_index = 1
        for edge in edges:
            edge_id = edge.get("id")
            if edge_id is None:
                while f"edge-{generated_index}" in edge_ids:
                    generated_index += 1
                edge_id = f"edge-{generated_index}"
                generated_index += 1
            if (
                edge.get("source") not in allowed
                or edge.get("target") not in allowed
                or not isinstance(edge.get("label", ""), str)
                or len(edge.get("label", "")) > 2000
            ):
                raise SceneError(
                    "Graph edges need unique IDs and existing source/target nodes"
                )
            if edge["source"] == edge["target"]:
                raise SceneError("Self-loop edges are not supported")
            edge_ids.add(edge_id)
            normalized_edges.append(
                {**edge, "id": edge_id, "label": edge.get("label", "")}
            )
        if direction not in ("horizontal", "vertical"):
            raise SceneError("direction must be horizontal or vertical")

        cluster_map = {}
        elements = []
        cluster_frames = []

        if clusters:
            if not isinstance(clusters, list):
                raise SceneError("clusters must be a list")
            c_ids = set()
            for c in clusters:
                cid = c.get("id") if isinstance(c, dict) else getattr(c, "id", None)
                if not cid or not isinstance(cid, str) or cid in c_ids:
                    raise SceneError("Cluster IDs must be unique non-empty strings")
                c_ids.add(cid)
            norm_clusters = [
                c if isinstance(c, dict) else c.model_dump() for c in clusters
            ]
            positioned, cluster_frames = clustered_layout(
                normalized_nodes,
                normalized_edges,
                norm_clusters,
                layout=layout,
                direction=direction,
            )
            for f in cluster_frames:
                frame_el = frame(
                    f["x"], f["y"], f["w"], f["h"], name=f["name"], **style
                )
                elements.append(frame_el)
                cluster_map[f["id"]] = frame_el["id"]
        else:
            if layout == "layered":
                positioned = layered_layout(
                    normalized_nodes, normalized_edges, direction
                )
            elif layout in ("horizontal", "vertical"):
                positioned = linear_layout(normalized_nodes, layout)
            else:
                raise SceneError("layout must be layered, horizontal or vertical")

        id_map, positioned_map = (
            {},
            {node["id"]: node for node in positioned},
        )
        for node in positioned:
            f_id = cluster_map.get(node.get("frame_id"))
            group = _shape_elements(
                node["shape"],
                node["x"],
                node["y"],
                node["w"],
                node["h"],
                node["label"],
                style,
                frame_id=f_id,
            )
            elements.extend(group)
            id_map[node["id"]] = {
                "element_id": group[0]["id"],
                "label_id": group[1]["id"] if len(group) > 1 else None,
            }
        edge_map = {}
        for edge in normalized_edges:
            source, target = (
                positioned_map[edge["source"]],
                positioned_map[edge["target"]],
            )
            start, end = boundary_point(source, target, 1), boundary_point(
                target, source, -1
            )
            edge_elbowed = edge.get("elbowed", elbowed)
            connector = arrow(*start, *end, elbowed=edge_elbowed, **style)
            connector["startBinding"] = {
                "elementId": id_map[edge["source"]]["element_id"],
                "focus": 0,
                "gap": 0,
                "fixedPoint": [0.5, 0.5],
                "mode": "inside",
            }
            connector["endBinding"] = {
                "elementId": id_map[edge["target"]]["element_id"],
                "focus": 0,
                "gap": 0,
                "fixedPoint": [0.5, 0.5],
                "mode": "inside",
            }
            elements.append(connector)
            label_id = None
            if edge["label"]:
                label_el = text(
                    (start[0] + end[0]) / 2,
                    (start[1] + end[1]) / 2,
                    edge["label"],
                    fontSize=14,
                    **style,
                )
                bind_text(label_el, connector)
                _center_label(label_el, connector)
                elements.append(label_el)
                label_id = label_el["id"]
            edge_map[edge["id"]] = {
                "element_id": connector["id"],
                "label_id": label_id,
            }
        self.state.replace(new_document(elements), expected_revision=revision)
        result = {
            "status": "graph drawn",
            "nodes": len(nodes),
            "edges": len(edges),
            "node_map": id_map,
            "edge_map": edge_map,
            "revision": self.state.revision,
        }
        if clusters:
            result["cluster_map"] = cluster_map
        return result
