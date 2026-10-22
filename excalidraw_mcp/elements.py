import uuid
import random
import time


# Explicit project defaults; never depend on the editor's current UI defaults.
DEFAULT_STYLE = {
    "strokeColor": "#1e1e1e",
    "backgroundColor": "transparent",
    "fillStyle": "solid",
    "strokeWidth": 2,
    "strokeStyle": "solid",
    "roughness": 1,
    "opacity": 100,
    "angle": 0,
}


def _apply_style(el: dict, style_kwargs: dict):
    """Merge style keyword arguments into an element dict, using defaults where not specified."""
    for key in DEFAULT_STYLE:
        if key in style_kwargs and style_kwargs[key] is not None:
            el[key] = style_kwargs[key]
        else:
            el[key] = DEFAULT_STYLE[key]
    # seed is required by Excalidraw for rendering
    el["seed"] = random.randint(1, 1000000)
    el["version"] = 1
    el["versionNonce"] = random.randrange(1, 2**31)
    el["updated"] = time.time_ns() // 1_000_000

    roundness_val = None
    if "roundness" in style_kwargs and style_kwargs["roundness"] is not None:
        r = style_kwargs["roundness"]
        if r == "adaptive":
            roundness_val = {"type": 3}
        elif r == "round":
            roundness_val = {"type": 2}
        elif r == "sharp":
            roundness_val = None
        elif isinstance(r, dict):
            roundness_val = r

    frame_id = style_kwargs.get("frameId") or style_kwargs.get("frame_id")

    el.update(
        index=None,
        groupIds=[],
        frameId=frame_id,
        boundElements=[],
        link=None,
        locked=False,
        isDeleted=False,
        roundness=roundness_val,
    )


def _base_shape(shape_type: str, x: int, y: int, w: int, h: int, **style):
    el = {
        "id": str(uuid.uuid4()),
        "type": shape_type,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
    }
    _apply_style(el, style)
    return el


def rect(x: int, y: int, w: int, h: int, **style):
    return _base_shape("rectangle", x, y, w, h, **style)


def ellipse(x: int, y: int, w: int, h: int, **style):
    return _base_shape("ellipse", x, y, w, h, **style)


def diamond(x: int, y: int, w: int, h: int, **style):
    return _base_shape("diamond", x, y, w, h, **style)


def frame(x: int, y: int, w: int, h: int, name: str = "", **style):
    el = {
        "id": str(uuid.uuid4()),
        "type": "frame",
        "name": name,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
    }
    _apply_style(el, style)
    return el


def text(x: int, y: int, content: str, fontSize: int = 20, **style):
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    el = {
        "id": str(uuid.uuid4()),
        "type": "text",
        "x": x,
        "y": y,
        "text": content,
        "fontSize": fontSize,
        "width": max(map(len, content.split("\n"))) * fontSize * 0.6,
        "height": len(content.split("\n")) * fontSize * 1.25,
        "fontFamily": 2,
        "lineHeight": 1.25,
        "textAlign": "left",
        "verticalAlign": "top",
        "originalText": content,
        "autoResize": True,
        "containerId": None,
    }
    _apply_style(el, style)
    return el


def arrow(x, y, x2, y2, elbowed=False, **style):
    is_elbowed = bool(style.pop("elbowed", elbowed))
    el = {
        "id": str(uuid.uuid4()),
        "type": "arrow",
        "x": x,
        "y": y,
        "points": [[0, 0], [x2 - x, y2 - y]],
        "width": abs(x2 - x),
        "height": abs(y2 - y),
        "startBinding": None,
        "endBinding": None,
        "startArrowhead": None,
        "endArrowhead": "arrow",
        "lastCommittedPoint": None,
        "elbowed": is_elbowed,
    }
    _apply_style(el, style)
    return el


def bind_text(text_el: dict, container_el: dict):
    """Bind a text element as the label of a container shape."""
    text_el["containerId"] = container_el["id"]
    text_el["textAlign"] = "center"
    text_el["verticalAlign"] = "middle"
    text_el["angle"] = container_el.get("angle", 0)

    text_id = text_el["id"]
    if container_el.get("boundElements") is None:
        container_el["boundElements"] = []

    # Avoid duplicates if bind_text is called multiple times
    if not any(b["id"] == text_id for b in container_el["boundElements"]):
        container_el["boundElements"].append({"type": "text", "id": text_id})
