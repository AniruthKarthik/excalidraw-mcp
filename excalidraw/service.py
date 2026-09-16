"""Scene operations independent of MCP transport and server globals."""
from excalidraw.elements import arrow, bind_text, diamond, ellipse, rect, text
from excalidraw.errors import SceneError
from excalidraw.document import serialize_document
from excalidraw.models import _finite_number, new_document
from excalidraw.scene import load_scene, save_scene
from excalidraw.state import SceneState
from layout import horizontal_layout
from parser import parse_architecture

SHAPES = {"rectangle": rect, "ellipse": ellipse, "diamond": diamond}


def _shape_elements(shape, x, y, w, h, label, style):
    shape_el = SHAPES[shape](x, y, w, h, **style)
    elements = [shape_el]
    if label:
        label_el = text(x + w // 4, y + h // 3, label, **style)
        bind_text(label_el, shape_el)
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


def _move_arrow_endpoints(el, dx, dy, start, end):
    if el.get("elbowed") or el.get("angle", 0):
        raise SceneError("Moving shapes attached to elbowed or rotated arrows is not supported yet")
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

    def add_shape(self, shape, x, y, w, h, label="", **style):
        elements = _shape_elements(shape, x, y, w, h, label, style)
        ids = self.state.add_many(elements)
        key = {"rectangle": "rectangle_id", "ellipse": "circle_id", "diamond": "diamond_id"}[shape]
        return {key: ids[0], "label_id": ids[1] if len(ids) > 1 else None}

    def add_arrow(self, x, y, x2, y2, label="", **style):
        arrow_el = arrow(x, y, x2, y2, **style)
        elements = [arrow_el]
        if label:
            label_el = text((x + x2) // 2, (y + y2) // 2, label, fontSize=14, **style)
            bind_text(label_el, arrow_el)
            elements.append(label_el)
        ids = self.state.add_many(elements)
        return {"arrow_id": ids[0], "label_id": ids[1] if len(ids) > 1 else None}

    def clear(self):
        self.state.clear()
        return {"status": "scene cleared"}

    def delete(self, element_id):
        def remove(document):
            index = _active(document)
            _require(index, element_id)
            removed = {element_id}
            removed.update(el["id"] for el in index.values() if el.get("containerId") == element_id)
            document["elements"] = [el for el in document["elements"] if el["id"] not in removed]
            for el in document["elements"]:
                if el["type"] == "arrow" and not el.get("isDeleted"):
                    for end in ("startBinding", "endBinding"):
                        if (el.get(end) or {}).get("elementId") in removed:
                            el[end] = None
            return {"status": "deleted", "element_id": element_id,
                    "deleted_ids": [key for key in index if key in removed]}
        return self.state.apply(remove)

    def move(self, element_id, x, y):
        if not _finite_number(x) or not _finite_number(y):
            raise SceneError("Move coordinates must be finite numbers")

        def move_elements(document):
            index = _active(document)
            el = _require(index, element_id)
            if el.get("containerId"):
                raise SceneError("Move the label's container instead of moving bound text independently")
            dx, dy = x - el["x"], y - el["y"]
            if not dx and not dy:
                return {"status": "moved", "element_id": element_id, "x": x, "y": y}
            if el["type"] == "arrow" and el.get("elbowed"):
                raise SceneError("Moving elbowed arrows is not supported yet")
            _translate(el, dx, dy)
            moved_targets = {element_id}
            owned_labels = {
                label["containerId"]: label for label in index.values()
                if label.get("containerId")
            }
            for label in index.values():
                if label.get("containerId") == element_id:
                    _translate(label, dx, dy)
                    moved_targets.add(label["id"])
            if el["type"] == "arrow":
                # A coordinate move intentionally detaches the arrow from shapes.
                el["startBinding"] = None
                el["endBinding"] = None
            for connector in index.values():
                if connector["type"] != "arrow" or connector["id"] == element_id:
                    continue
                start = (connector.get("startBinding") or {}).get("elementId") in moved_targets
                end = (connector.get("endBinding") or {}).get("elementId") in moved_targets
                if start or end:
                    _move_arrow_endpoints(connector, dx, dy, start, end)
                    # Preserve the label's offset from the endpoint midpoint.
                    label = owned_labels.get(connector["id"])
                    if label:
                        _translate(label, dx * (int(start) + int(end)) / 2,
                                   dy * (int(start) + int(end)) / 2)
            return {"status": "moved", "element_id": element_id, "x": x, "y": y}
        return self.state.apply(move_elements)

    def save(self, name, overwrite=False):
        document = self.state.document()
        path = save_scene(name, document, overwrite=overwrite)
        return {"path": path, "elements": len(document["elements"]), "status": "saved"}

    def export_scene(self):
        """Export a detached snapshot without filesystem access."""
        return serialize_document(self.state.document())

    def load(self, name):
        revision = self.state.revision
        document = load_scene(name)
        self.state.replace(document, expected_revision=revision)
        return {"loaded": len(document["elements"]), "name": name, "status": "scene loaded"}

    def preview(self):
        raise SceneError(
            "Browser preview is not implemented. Use save(name) for a server-local file "
            "or export_scene() for an embedded document, then import it into Excalidraw."
        )

    def draw_architecture(self, prompt, **style):
        revision = self.state.revision
        nodes = parse_architecture(prompt)
        if not nodes or any(not node["label"].strip() for node in nodes):
            raise SceneError("Provide at least one nonempty component label, e.g. 'box: API, box: Database'")
        positioned = horizontal_layout(nodes)
        elements = []
        previous = None
        for node in positioned:
            group = _shape_elements(node["shape"], node["x"], node["y"], node["w"], node["h"], node["label"], style)
            elements.extend(group)
            current = group[0]
            if previous:
                connector = arrow(
                    previous["x"] + previous["width"] / 2,
                    previous["y"] + previous["height"] / 2,
                    current["x"] + current["width"] / 2,
                    current["y"] + current["height"] / 2, **style,
                )
                connector["startBinding"] = {"elementId": previous["id"], "fixedPoint": [0.5, 0.5], "mode": "inside"}
                connector["endBinding"] = {"elementId": current["id"], "fixedPoint": [0.5, 0.5], "mode": "inside"}
                elements.append(connector)
            previous = current
        self.state.replace(new_document(elements), expected_revision=revision)
        return {"nodes": len(positioned), "url": None, "status": "architecture drawn",
                "next_step": "Use save(name), then open the saved .excalidraw file in Excalidraw."}
