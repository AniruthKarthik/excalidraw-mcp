import uuid
import random
import time


# Default style values that match Excalidraw's defaults
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


def text(x: int, y: int, content: str, fontSize: int = 20, **style):
    el = {
        "id": str(uuid.uuid4()),
        "type": "text",
        "x": x,
        "y": y,
        "text": content,
        "fontSize": fontSize,
        "width": len(content) * fontSize * 0.6,
        "height": fontSize * 1.5,
    }
    _apply_style(el, style)
    return el


def arrow(x, y, x2, y2, **style):
    el = {
        "id": str(uuid.uuid4()),
        "type": "arrow",
        "x": x,
        "y": y,
        "points": [[0, 0], [x2 - x, y2 - y]],
    }
    _apply_style(el, style)
    return el


def bind_text(text_el: dict, container_el: dict):
    """Bind a text element as the label of a container shape."""
    text_el["containerId"] = container_el["id"]

    text_id = text_el["id"]
    if container_el.get("boundElements") is None:
        container_el["boundElements"] = []

    # Avoid duplicates if bind_text is called multiple times
    if not any(b["id"] == text_id for b in container_el["boundElements"]):
        container_el["boundElements"].append({"type": "text", "id": text_id})
