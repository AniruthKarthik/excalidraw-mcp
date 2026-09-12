from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from excalidraw.scene import save_scene, load_scene, new_document
from excalidraw.errors import SceneError
from excalidraw.elements import rect, ellipse, diamond, text, arrow, bind_text
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


def _style_kwargs(
    strokeColor: str | None = None,
    backgroundColor: str | None = None,
    fillStyle: str | None = None,
    strokeWidth: int | None = None,
    strokeStyle: str | None = None,
    opacity: int | None = None,
    roughness: int | None = None,
) -> dict:
    """Collect non-None style keyword arguments into a dict."""
    return {k: v for k, v in locals().items() if v is not None}


@mcp.tool
def add_rectangle(
    x: int,
    y: int,
    w: int,
    h: int,
    label: str = "",
    strokeColor: str | None = None,
    backgroundColor: str | None = None,
    fillStyle: str | None = None,
    strokeWidth: int | None = None,
    strokeStyle: str | None = None,
    opacity: int | None = None,
    roughness: int | None = None,
):
    """Add a rectangle to the scene.

    Style parameters are optional — when omitted, Excalidraw defaults are used.
    """
    style = _style_kwargs(
        strokeColor=strokeColor,
        backgroundColor=backgroundColor,
        fillStyle=fillStyle,
        strokeWidth=strokeWidth,
        strokeStyle=strokeStyle,
        opacity=opacity,
        roughness=roughness,
    )
    r = rect(x, y, w, h, **style)
    rect_id = scene.add(r)

    if label:
        t = text(x + w // 4, y + h // 3, label, **style)
        bind_text(t, r)
        scene.add(t)

    return {"rectangle_id": rect_id}


@mcp.tool
def add_circle(
    x: int,
    y: int,
    size: int,
    label: str = "",
    strokeColor: str | None = None,
    backgroundColor: str | None = None,
    fillStyle: str | None = None,
    strokeWidth: int | None = None,
    strokeStyle: str | None = None,
    opacity: int | None = None,
    roughness: int | None = None,
):
    """Add a circle (ellipse) to the scene."""
    style = _style_kwargs(
        strokeColor=strokeColor,
        backgroundColor=backgroundColor,
        fillStyle=fillStyle,
        strokeWidth=strokeWidth,
        strokeStyle=strokeStyle,
        opacity=opacity,
        roughness=roughness,
    )
    c = ellipse(x, y, size, size, **style)
    circle_id = scene.add(c)

    if label:
        t = text(x + size // 4, y + size // 3, label, **style)
        bind_text(t, c)
        scene.add(t)

    return {"circle_id": circle_id}


@mcp.tool
def add_diamond(
    x: int,
    y: int,
    w: int,
    h: int,
    label: str = "",
    strokeColor: str | None = None,
    backgroundColor: str | None = None,
    fillStyle: str | None = None,
    strokeWidth: int | None = None,
    strokeStyle: str | None = None,
    opacity: int | None = None,
    roughness: int | None = None,
):
    """Add a diamond to the scene."""
    style = _style_kwargs(
        strokeColor=strokeColor,
        backgroundColor=backgroundColor,
        fillStyle=fillStyle,
        strokeWidth=strokeWidth,
        strokeStyle=strokeStyle,
        opacity=opacity,
        roughness=roughness,
    )
    d = diamond(x, y, w, h, **style)
    diamond_id = scene.add(d)

    if label:
        t = text(x + w // 4, y + h // 3, label, **style)
        bind_text(t, d)
        scene.add(t)

    return {"diamond_id": diamond_id}


@mcp.tool
def add_arrow(
    x: int,
    y: int,
    x2: int,
    y2: int,
    label: str = "",
    strokeColor: str | None = None,
    strokeWidth: int | None = None,
    strokeStyle: str | None = None,
    opacity: int | None = None,
):
    """Add an arrow between two points.

    Optionally add a label (displayed as floating text near the arrow midpoint).
    """
    style = _style_kwargs(
        strokeColor=strokeColor,
        strokeWidth=strokeWidth,
        strokeStyle=strokeStyle,
        opacity=opacity,
    )
    a = arrow(x, y, x2, y2, **style)
    arrow_id = scene.add(a)

    if label:
        mid_x = (x + x2) // 2
        mid_y = (y + y2) // 2
        t = text(mid_x, mid_y, label, fontSize=14, **style)
        scene.add(t)

    return {"arrow_id": arrow_id}


@mcp.tool
def clear():
    """Remove all elements from the scene."""
    scene.clear()
    return {"status": "scene cleared"}


@mcp.tool
def delete(element_id: str):
    """Remove a single element by its ID."""
    scene.delete(element_id)
    return {"status": "deleted", "element_id": element_id}


@mcp.tool
def move(element_id: str, x: int, y: int):
    """Move an element to new (x, y) coordinates."""
    el = scene.get(element_id)

    if not el:
        return {"error": "not found", "element_id": element_id}

    el["x"] = x
    el["y"] = y

    return {"status": "moved", "element_id": element_id, "x": x, "y": y}


@mcp.tool
def save(name: str, overwrite: bool = False):
    """Save under a simple name (no extension). Set overwrite=true to replace an existing file."""
    document = scene.document()
    try:
        path = save_scene(name, document, overwrite=overwrite)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    return {"path": path, "elements": len(document["elements"]), "status": "saved"}


@mcp.tool
def load(name: str):
    """Replace the current scene with a saved document; invalid files leave it unchanged."""
    try:
        document = load_scene(name)
        scene.replace(document)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    return {"loaded": len(document["elements"]), "name": name, "status": "scene loaded"}


@mcp.tool
def preview():
    """Preview is unavailable. Save a .excalidraw file and open it in Excalidraw."""
    raise ToolError(
        "Browser preview is not implemented. Use save(name), then open the saved "
        ".excalidraw file in Excalidraw. The returned path is on the server."
    )


@mcp.tool
def draw_architecture(
    prompt: str,
    strokeColor: str | None = None,
    backgroundColor: str | None = None,
    fillStyle: str | None = None,
    strokeWidth: int | None = None,
    strokeStyle: str | None = None,
    opacity: int | None = None,
    roughness: int | None = None,
):
    """Replace the scene with a diagram from comma/newline-separated components.

    Supports ``"shape: label"`` syntax where shape can be
    ``rectangle``/``box``, ``circle``/``ellipse``, or ``diamond``.
    Components are arranged horizontally with automatic connectors.

    All style parameters are optional and apply globally to every element.
    """
    style = _style_kwargs(
        strokeColor=strokeColor,
        backgroundColor=backgroundColor,
        fillStyle=fillStyle,
        strokeWidth=strokeWidth,
        strokeStyle=strokeStyle,
        opacity=opacity,
        roughness=roughness,
    )

    nodes = parse_architecture(prompt)
    if not nodes or any(not node["label"].strip() for node in nodes):
        raise ToolError(
            "Provide at least one nonempty component label, "
            "e.g. 'box: API, box: Database'"
        )
    positioned = horizontal_layout(nodes)
    elements = []
    previous_center = None

    for node in positioned:
        shape_factory = SHAPES.get(node["shape"], rect)
        shape_el = shape_factory(node["x"], node["y"], node["w"], node["h"], **style)
        elements.append(shape_el)

        text_el = text(
            node["x"] + (node["w"] // 4),
            node["y"] + (node["h"] // 3),
            node["label"],
            **style,
        )
        bind_text(text_el, shape_el)
        elements.append(text_el)

        current_center = (
            node["x"] + (node["w"] // 2),
            node["y"] + (node["h"] // 2),
        )

        if previous_center:
            elements.append(
                arrow(
                    previous_center[0],
                    previous_center[1],
                    current_center[0],
                    current_center[1],
                    **style,
                )
            )

        previous_center = current_center

    try:
        scene.replace(new_document(elements))
    except SceneError as exc:
        raise ToolError(str(exc)) from exc
    return {
        "nodes": len(positioned), "url": None, "status": "architecture drawn",
        "next_step": "Use save(name), then open the saved .excalidraw file in Excalidraw.",
    }


if __name__ == "__main__":
    mcp.run()
