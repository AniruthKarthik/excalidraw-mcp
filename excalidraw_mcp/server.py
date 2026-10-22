"""MCP adapters; each server owns an explicit scene service."""

from hashlib import sha256

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import Image
from mcp.types import EmbeddedResource, TextResourceContents
from mcp.types import ToolAnnotations

from excalidraw_mcp.contracts import (
    ArchitectureResult,
    BatchOperation,
    BatchResult,
    Boolean,
    Color,
    ConnectResult,
    Coordinate,
    CreateResult,
    DeleteResult,
    Dimension,
    Direction,
    ElementId,
    ElementResult,
    ElementSummary,
    ElementType,
    FillStyle,
    FindResult,
    FontSize,
    GraphCluster,
    GraphEdge,
    GraphNode,
    GraphResult,
    Label,
    LayoutType,
    LoadResult,
    MoveResult,
    NonEmptyText,
    Offset,
    Opacity,
    PageLimit,
    PreviewPadding,
    PreviewScale,
    ResizeResult,
    Roughness,
    Roundness,
    SaveResult,
    SavedScenesResult,
    SceneName,
    ScenePage,
    StatusResult,
    StrokeStyle,
    StrokeWidth,
    UndoResult,
    UpdateResult,
)
from excalidraw_mcp.document import MIME_TYPE
from excalidraw_mcp.service import SceneService

MUTATING = ToolAnnotations(
    destructiveHint=False, idempotentHint=False, openWorldHint=False
)
READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)


def _style_kwargs(
    strokeColor: str | None = None,
    backgroundColor: str | None = None,
    fillStyle: str | None = None,
    strokeWidth: int | None = None,
    strokeStyle: str | None = None,
    opacity: int | None = None,
    roughness: int | None = None,
    roundness: str | None = None,
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

    @mcp.tool(annotations=MUTATING, run_in_thread=False)
    def add_rectangle(
        x: Coordinate,
        y: Coordinate,
        w: Dimension,
        h: Dimension,
        label: Label = "",
        roundness: Roundness | None = None,
        frame_id: ElementId | None = None,
        strokeColor: Color | None = None,
        backgroundColor: Color | None = None,
        fillStyle: FillStyle | None = None,
        strokeWidth: StrokeWidth | None = None,
        strokeStyle: StrokeStyle | None = None,
        opacity: Opacity | None = None,
        roughness: Roughness | None = None,
    ) -> CreateResult:
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
            roundness=roundness,
        )
        return invoke(
            service.add_shape, "rectangle", x, y, w, h, label, frame_id=frame_id, **style
        )

    @mcp.tool(annotations=MUTATING, run_in_thread=False)
    def add_circle(
        x: Coordinate,
        y: Coordinate,
        size: Dimension,
        label: Label = "",
        frame_id: ElementId | None = None,
        strokeColor: Color | None = None,
        backgroundColor: Color | None = None,
        fillStyle: FillStyle | None = None,
        strokeWidth: StrokeWidth | None = None,
        strokeStyle: StrokeStyle | None = None,
        opacity: Opacity | None = None,
        roughness: Roughness | None = None,
    ) -> CreateResult:
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
        return invoke(
            service.add_shape, "ellipse", x, y, size, size, label, frame_id=frame_id, **style
        )

    @mcp.tool(annotations=MUTATING, run_in_thread=False)
    def add_diamond(
        x: Coordinate,
        y: Coordinate,
        w: Dimension,
        h: Dimension,
        label: Label = "",
        roundness: Roundness | None = None,
        frame_id: ElementId | None = None,
        strokeColor: Color | None = None,
        backgroundColor: Color | None = None,
        fillStyle: FillStyle | None = None,
        strokeWidth: StrokeWidth | None = None,
        strokeStyle: StrokeStyle | None = None,
        opacity: Opacity | None = None,
        roughness: Roughness | None = None,
    ) -> CreateResult:
        """Add a diamond to the scene."""
        style = _style_kwargs(
            strokeColor=strokeColor,
            backgroundColor=backgroundColor,
            fillStyle=fillStyle,
            strokeWidth=strokeWidth,
            strokeStyle=strokeStyle,
            opacity=opacity,
            roughness=roughness,
            roundness=roundness,
        )
        return invoke(
            service.add_shape, "diamond", x, y, w, h, label, frame_id=frame_id, **style
        )

    @mcp.tool(annotations=MUTATING, run_in_thread=False)
    def add_arrow(
        x: Coordinate,
        y: Coordinate,
        x2: Coordinate,
        y2: Coordinate,
        label: Label = "",
        elbowed: Boolean = False,
        strokeColor: Color | None = None,
        strokeWidth: StrokeWidth | None = None,
        strokeStyle: StrokeStyle | None = None,
        opacity: Opacity | None = None,
        roughness: Roughness | None = None,
    ) -> CreateResult:
        """Add an arrow between two points.

        Optionally add bound text near the arrow midpoint.
        """
        style = _style_kwargs(
            strokeColor=strokeColor,
            strokeWidth=strokeWidth,
            strokeStyle=strokeStyle,
            opacity=opacity,
            roughness=roughness,
        )
        return invoke(service.add_arrow, x, y, x2, y2, label, elbowed=elbowed, **style)

    @mcp.tool(annotations=MUTATING, run_in_thread=False)
    def add_frame(
        name: Label,
        x: Coordinate,
        y: Coordinate,
        w: Dimension,
        h: Dimension,
        element_ids: list[ElementId] | None = None,
        strokeColor: Color | None = None,
        backgroundColor: Color | None = None,
        fillStyle: FillStyle | None = None,
        strokeWidth: StrokeWidth | None = None,
        strokeStyle: StrokeStyle | None = None,
        opacity: Opacity | None = None,
        roughness: Roughness | None = None,
    ) -> CreateResult:
        """Add a frame (boundary container) to the scene.

        Optionally assign existing elements to this frame using `element_ids`.
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
        return invoke(
            service.add_frame,
            name,
            x,
            y,
            w,
            h,
            element_ids=element_ids,
            **style,
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            destructiveHint=True, idempotentHint=True, openWorldHint=False
        ),
        run_in_thread=False,
    )
    def clear() -> StatusResult:
        """Remove all elements, app state and files from the scene."""
        return invoke(service.clear)

    @mcp.tool(
        annotations=ToolAnnotations(
            destructiveHint=True, idempotentHint=False, openWorldHint=False
        ),
        run_in_thread=False,
    )
    def delete(element_id: ElementId) -> DeleteResult:
        """Delete an element and its owned label; detach surviving connectors."""
        return invoke(service.delete, element_id)

    @mcp.tool(
        annotations=ToolAnnotations(idempotentHint=True, openWorldHint=False),
        run_in_thread=False,
    )
    def move(element_id: ElementId, x: Coordinate, y: Coordinate) -> MoveResult:
        """Move an element and its label. Shape connectors follow; directly moved arrows detach."""
        return invoke(service.move, element_id, x, y)

    @mcp.tool(
        annotations=ToolAnnotations(destructiveHint=True, openWorldHint=True),
        run_in_thread=False,
    )
    def save(name: SceneName, overwrite: Boolean = False) -> SaveResult:
        """Save a consistent snapshot. Set overwrite=true to replace an existing file."""
        return invoke(service.save, name, overwrite=overwrite)

    @mcp.tool(annotations=READ_ONLY, run_in_thread=False)
    def get_scene(offset: Offset = 0, limit: PageLimit = 50) -> ScenePage:
        """List active elements with pagination and the current revision."""
        return invoke(service.get_scene, offset, limit)

    @mcp.tool(annotations=READ_ONLY, run_in_thread=False)
    def get_element(element_id: ElementId) -> ElementResult:
        """Return one active element by ID."""
        return invoke(service.get_element, element_id)

    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
        run_in_thread=False,
    )
    def list_saved_scenes() -> SavedScenesResult:
        """List scene names available in the configured storage directory."""
        return invoke(service.list_saved_scenes)

    @mcp.tool(annotations=MUTATING, run_in_thread=False)
    def add_text(
        x: Coordinate,
        y: Coordinate,
        content: NonEmptyText,
        font_size: FontSize = 20,
        frame_id: ElementId | None = None,
        strokeColor: Color | None = None,
        opacity: Opacity | None = None,
    ) -> CreateResult:
        """Add standalone text and return its element ID."""
        return invoke(
            service.add_text,
            x,
            y,
            content,
            font_size,
            frame_id=frame_id,
            **_style_kwargs(strokeColor=strokeColor, opacity=opacity),
        )

    @mcp.tool(
        annotations=ToolAnnotations(idempotentHint=True, openWorldHint=False),
        run_in_thread=False,
    )
    def update_element(
        element_id: ElementId,
        label: Label | None = None,
        roundness: Roundness | None = None,
        frame_id: ElementId | None = None,
        elbowed: Boolean | None = None,
        strokeColor: Color | None = None,
        backgroundColor: Color | None = None,
        fillStyle: FillStyle | None = None,
        strokeWidth: StrokeWidth | None = None,
        strokeStyle: StrokeStyle | None = None,
        opacity: Opacity | None = None,
        roughness: Roughness | None = None,
    ) -> UpdateResult:
        """Update a label and/or styles. An empty label removes an existing label."""
        return invoke(
            service.update_element,
            element_id,
            label,
            strokeColor,
            backgroundColor,
            fillStyle,
            strokeWidth,
            strokeStyle,
            opacity,
            roughness,
            roundness=roundness,
            frame_id=frame_id,
            elbowed=elbowed,
        )

    @mcp.tool(
        annotations=ToolAnnotations(idempotentHint=True, openWorldHint=False),
        run_in_thread=False,
    )
    def resize(
        element_id: ElementId, width: Dimension, height: Dimension
    ) -> ResizeResult:
        """Resize a shape and recenter its label."""
        return invoke(service.resize, element_id, width, height)

    @mcp.tool(annotations=MUTATING, run_in_thread=False)
    def connect(
        source_id: ElementId,
        target_id: ElementId,
        label: Label = "",
        elbowed: Boolean = False,
        strokeColor: Color | None = None,
        strokeWidth: StrokeWidth | None = None,
        strokeStyle: StrokeStyle | None = None,
        opacity: Opacity | None = None,
        roughness: Roughness | None = None,
    ) -> ConnectResult:
        """Connect two existing shapes by ID with a bound arrow."""
        return invoke(
            service.connect,
            source_id,
            target_id,
            label,
            elbowed=elbowed,
            **_style_kwargs(
                strokeColor=strokeColor,
                strokeWidth=strokeWidth,
                strokeStyle=strokeStyle,
                opacity=opacity,
                roughness=roughness,
            ),
        )

    @mcp.tool(annotations=READ_ONLY, run_in_thread=False)
    def find_elements(
        query: str | None = None,
        type: ElementType | None = None,
        frame_id: ElementId | None = None,
        element_id: ElementId | None = None,
        connected_to: ElementId | None = None,
        include_bound_labels: bool = False,
        limit: PageLimit = 50,
    ) -> FindResult:
        """Find active elements matching query string, type, frame, or connection criteria."""
        return invoke(
            service.find_elements,
            query=query,
            type=type,
            frame_id=frame_id,
            element_id=element_id,
            connected_to=connected_to,
            include_bound_labels=include_bound_labels,
            limit=limit,
        )

    @mcp.tool(annotations=MUTATING, run_in_thread=False)
    def batch_mutate(
        operations: list[BatchOperation],
    ) -> BatchResult:
        """Atomically execute a batch of creation, editing, and deletion operations."""
        return invoke(
            service.batch_mutate,
            [op.model_dump(exclude_unset=False) for op in operations],
        )

    @mcp.tool(
        annotations=ToolAnnotations(destructiveHint=True, openWorldHint=False),
        run_in_thread=False,
    )
    def undo() -> UndoResult:
        """Restore the scene before the most recent successful mutation."""
        return invoke(service.undo)

    @mcp.tool(annotations=READ_ONLY, run_in_thread=False)
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

    @mcp.tool(
        annotations=ToolAnnotations(destructiveHint=True, openWorldHint=True),
        run_in_thread=False,
    )
    def load(name: SceneName) -> LoadResult:
        """Replace the scene with a saved document; concurrent changes cause a retry error."""
        return invoke(service.load, name)

    @mcp.resource("excalidraw://scenes/{name}.excalidraw", mime_type=MIME_TYPE)
    def saved_scene_resource(name: SceneName) -> str:
        """Read a validated saved scene without changing the active scene."""
        return invoke(service.read_saved_scene, name)

    @mcp.tool(annotations=READ_ONLY, run_in_thread=False)
    def preview(
        scale: PreviewScale = 1.0,
        padding: PreviewPadding = 40,
    ) -> Image:
        """Render an inline PNG image preview of the active Excalidraw canvas."""
        data = invoke(service.preview, scale=scale, padding=padding)
        return Image(data=data, format="png")

    @mcp.tool(
        annotations=ToolAnnotations(destructiveHint=True, openWorldHint=False),
        run_in_thread=False,
    )
    def draw_architecture(
        prompt: NonEmptyText,
        strokeColor: Color | None = None,
        backgroundColor: Color | None = None,
        fillStyle: FillStyle | None = None,
        strokeWidth: StrokeWidth | None = None,
        strokeStyle: StrokeStyle | None = None,
        opacity: Opacity | None = None,
        roughness: Roughness | None = None,
    ) -> ArchitectureResult:
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

    @mcp.tool(
        annotations=ToolAnnotations(destructiveHint=True, openWorldHint=False),
        run_in_thread=False,
    )
    def draw_graph(
        nodes: list[GraphNode],
        edges: list[GraphEdge],
        clusters: list[GraphCluster] | None = None,
        layout: LayoutType = "layered",
        direction: Direction = "horizontal",
        elbowed: Boolean = False,
        roundness: Roundness | None = None,
    ) -> GraphResult:
        """Replace the scene with a structured graph and return stable ID mappings."""
        return invoke(
            service.draw_graph,
            [node.model_dump() for node in nodes],
            [edge.model_dump() for edge in edges],
            clusters=[cluster.model_dump() for cluster in clusters]
            if clusters
            else None,
            layout=layout,
            direction=direction,
            elbowed=elbowed,
            roundness=roundness,
        )

    return mcp


mcp = create_server()


def main():
    """Run the installed stdio MCP server."""
    mcp.run()


def run():
    """Run the installed stdio MCP server."""
    mcp.run(show_banner=False)


if __name__ == "__main__":
    main()
