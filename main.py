from fastmcp import FastMCP
from excalidraw.scene import save_scene
from excalidraw.elements import rect, text, arrow

mcp = FastMCP("Excalidraw MCP")

current_scene = []


@mcp.tool
def add_rectangle(x: int, y: int, w: int, h: int, label=""):
    r = rect(x, y, w, h)
    current_scene.append(r)

    if label:
        current_scene.append(text(x + w // 4, y + h // 3, label))

    return "rectangle added"


@mcp.tool
def add_arrow(x: int, y: int, x2: int, y2: int):
    current_scene.append(arrow(x, y, x2, y2))
    return "arrow added"


@mcp.tool
def save(name: str):
    return save_scene(name, current_scene)


if __name__ == "__main__":
    mcp.run()
