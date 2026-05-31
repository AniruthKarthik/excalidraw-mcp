import uuid


def _base_shape(shape_type: str, x: int, y: int, w: int, h: int):
    return {
        "id": str(uuid.uuid4()),
        "type": shape_type,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
    }


def rect(x: int, y: int, w: int, h: int):
    return _base_shape("rectangle", x, y, w, h)


def ellipse(x: int, y: int, w: int, h: int):
    return _base_shape("ellipse", x, y, w, h)


def diamond(x: int, y: int, w: int, h: int):
    return _base_shape("diamond", x, y, w, h)


def text(x: int, y: int, content: str):
    return {
        "id": str(uuid.uuid4()),
        "type": "text",
        "x": x,
        "y": y,
        "text": content,
        "fontSize": 20,
        "width": len(content) * 12,
        "height": 30,
    }


def arrow(x, y, x2, y2):
    return {
        "id": str(uuid.uuid4()),
        "type": "arrow",
        "x": x,
        "y": y,
        "points": [[0, 0], [x2 - x, y2 - y]],
    }
