import uuid


def rect(x: int, y: int, w: int, h: int):
    rect_id = str(uuid.uuid4())

    return {
        "id": rect_id,
        "type": "rectangle",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
    }


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
