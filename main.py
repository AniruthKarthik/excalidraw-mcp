from fastmcp import FastMCP
from excalidraw.scene import save_scene, open_scene
from excalidraw.elements import rect, ellipse, diamond, text, arrow
from excalidraw.state import SceneState
from parser import parse_architecture
from layout import horizontal_layout

mcp = FastMCP("Excalidraw MCP")

scene = SceneState()
SHAPES = {
    "rectangle": rect,
    "ellipse": ellipse,
    "diamond": diamond,
}


@mcp.tool
def add_rectangle(x: int, y: int, w: int, h: int, label=""):
    r = rect(x, y, w, h)
    rect_id = scene.add(r)

    if label:
        scene.add(text(x + w // 4, y + h // 3, label))

    return {"rectangle_id": rect_id}


@mcp.tool
def add_circle(x: int, y: int, size: int, label=""):
    c = ellipse(x, y, size, size)
    circle_id = scene.add(c)

    if label:
        scene.add(text(x + size // 4, y + size // 3, label))

    return {"circle_id": circle_id}


@mcp.tool
def add_diamond(x: int, y: int, w: int, h: int, label=""):
    d = diamond(x, y, w, h)
    diamond_id = scene.add(d)

    if label:
        scene.add(text(x + w // 4, y + h // 3, label))

    return {"diamond_id": diamond_id}


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


@mcp.tool
def draw_architecture(prompt: str):

    scene.clear()
    nodes = parse_architecture(prompt)
    positioned = horizontal_layout(nodes)
    previous_center = None

    for node in positioned:
        shape_factory = SHAPES.get(node["shape"], rect)
        scene.add(shape_factory(node["x"], node["y"], node["w"], node["h"]))

        scene.add(
            text(
                node["x"] + (node["w"] // 4),
                node["y"] + (node["h"] // 3),
                node["label"],
            )
        )

        current_center = (
            node["x"] + (node["w"] // 2),
            node["y"] + (node["h"] // 2),
        )

        if previous_center:
            scene.add(
                arrow(
                    previous_center[0],
                    previous_center[1],
                    current_center[0],
                    current_center[1],
                )
            )

        previous_center = current_center

    open_scene(scene.all())

    return {"nodes": len(positioned), "status": "architecture drawn"}


if __name__ == "__main__":
    mcp.run()
