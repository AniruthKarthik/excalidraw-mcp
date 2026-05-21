from fastmcp import FastMCP
from excalidraw.scene import save_scene, open_scene
from excalidraw.elements import rect, text, arrow
from excalidraw.state import SceneState

mcp = FastMCP("Excalidraw MCP")

scene = SceneState()


@mcp.tool
def add_rectangle(x: int, y: int, w: int, h: int, label=""):
    r = rect(x, y, w, h)
    rect_id = scene.add(r)

    if label:
        scene.add(text(x + w // 4, y + h // 3, label))

    return {"rectangle_id": rect_id}


@mcp.tool
def add_arrow(x: int, y: int, x2: int, y2: int):
    a = arrow(x, y, x2, y2)
    arrow_id = scene.add(a)

    return {"arrow_id": arrow_id}


@mcp.tool
def clear():
    scene.clear()
    return "scene cleared"


@mcp.tool
def delete(element_id: str):
    scene.delete(element_id)
    return "deleted"


@mcp.tool
def move(element_id: str, x: int, y: int):
    el = scene.get(element_id)

    if not el:
        return "not found"

    el["x"] = x
    el["y"] = y

    return "moved"


@mcp.tool
def save(name: str):
    return save_scene(name, scene.all())


@mcp.tool
def preview():
    return open_scene(scene.all())


if __name__ == "__main__":
    mcp.run()
