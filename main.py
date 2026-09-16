"""MCP adapters; each server owns an explicit scene service."""
from hashlib import sha256

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import EmbeddedResource, TextResourceContents

from excalidraw.document import MIME_TYPE
from excalidraw.service import SceneService


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


def create_server(service: SceneService | None = None) -> FastMCP:
    service = service if service is not None else SceneService()
    mcp = FastMCP("Excalidraw MCP")

    def invoke(operation, *args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc

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
        return invoke(service.add_shape, "rectangle", x, y, w, h, label, **style)


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
        return invoke(service.add_shape, "ellipse", x, y, size, size, label, **style)


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
        return invoke(service.add_shape, "diamond", x, y, w, h, label, **style)


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

        Optionally add bound text near the arrow midpoint.
        """
        style = _style_kwargs(
            strokeColor=strokeColor,
            strokeWidth=strokeWidth,
            strokeStyle=strokeStyle,
            opacity=opacity,
        )
        return invoke(service.add_arrow, x, y, x2, y2, label, **style)


    @mcp.tool
    def clear():
        """Remove all elements, app state and files from the scene."""
        return invoke(service.clear)


    @mcp.tool
    def delete(element_id: str):
        """Delete an element and its owned label; detach surviving connectors."""
        return invoke(service.delete, element_id)


    @mcp.tool
    def move(element_id: str, x: int, y: int):
        """Move an element and its label. Shape connectors follow; directly moved arrows detach."""
        return invoke(service.move, element_id, x, y)


    @mcp.tool
    def save(name: str, overwrite: bool = False):
        """Save a consistent snapshot. Set overwrite=true to replace an existing file."""
        return invoke(service.save, name, overwrite=overwrite)

    @mcp.tool
    def export_scene():
        """Return an embedded .excalidraw document for the client to save/import. No file is written."""
        payload = invoke(service.export_scene)
        snapshot_id = sha256(payload.encode("utf-8")).hexdigest()
        return EmbeddedResource(
            type="resource",
            resource=TextResourceContents(
                uri=f"excalidraw://export/{snapshot_id}/scene.excalidraw",
                mimeType=MIME_TYPE,
                text=payload,
            ),
        )


    @mcp.tool
    def load(name: str):
        """Replace the scene with a saved document; concurrent changes cause a retry error."""
        return invoke(service.load, name)


    @mcp.tool
    def preview():
        """Preview is unavailable. Save a .excalidraw file and open it in Excalidraw."""
        return invoke(service.preview)


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
        return invoke(service.draw_architecture, prompt, **style)

    return mcp


mcp = create_server()


if __name__ == "__main__":
    mcp.run()
