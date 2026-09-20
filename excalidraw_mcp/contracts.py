"""Types shared by MCP schemas and structured graph operations."""

from typing import Annotated, Any, Literal, NotRequired, TypedDict

from pydantic import BaseModel, ConfigDict, Field, model_validator

from excalidraw_mcp.validation import COLOR_PATTERN

Coordinate = Annotated[float, Field(strict=True, ge=-100_000, le=100_000)]
Dimension = Annotated[float, Field(strict=True, gt=0, le=100_000)]
Label = Annotated[str, Field(strict=True, max_length=2_000)]
ElementId = Annotated[
    str, Field(strict=True, min_length=1, max_length=200, pattern=r".*\S.*")
]
Color = Annotated[str, Field(strict=True, pattern=f"^{COLOR_PATTERN}$")]
Boolean = Annotated[bool, Field(strict=True)]
SceneName = Annotated[
    str,
    Field(strict=True, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$"),
]
Opacity = Annotated[int, Field(strict=True, ge=0, le=100)]
StrokeWidth = Annotated[int, Field(strict=True, ge=1, le=20)]
FontSize = Annotated[int, Field(strict=True, ge=8, le=200)]
Roughness = Annotated[int, Field(strict=True, ge=0, le=3)]
FillStyle = Literal["solid", "hachure", "cross-hatch", "zigzag"]
StrokeStyle = Literal["solid", "dashed", "dotted"]
ShapeType = Literal["rectangle", "ellipse", "diamond"]
LayoutType = Literal["layered", "horizontal", "vertical"]
Direction = Literal["horizontal", "vertical"]
Offset = Annotated[int, Field(ge=0)]
PageLimit = Annotated[int, Field(ge=1, le=200)]


class GraphNode(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: ElementId
    label: Annotated[
        str, Field(strict=True, min_length=1, max_length=2_000, pattern=r".*\S.*")
    ]
    shape: ShapeType = "rectangle"


class GraphEdge(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: ElementId | None = None
    source: ElementId
    target: ElementId
    label: Label = ""

    @model_validator(mode="after")
    def distinct_ends(self):
        if self.source == self.target:
            raise ValueError("source and target must differ")
        return self


class CreateResult(TypedDict):
    rectangle_id: NotRequired[str]
    circle_id: NotRequired[str]
    diamond_id: NotRequired[str]
    arrow_id: NotRequired[str]
    text_id: NotRequired[str]
    label_id: NotRequired[str | None]


class StatusResult(TypedDict):
    status: str


class ElementResult(TypedDict):
    element: dict[str, Any]
    revision: int


class ScenePage(TypedDict):
    revision: int
    total: int
    offset: int
    limit: int
    elements: list[dict[str, Any]]
    has_more: bool


class GraphResult(TypedDict):
    status: str
    nodes: int
    edges: int
    node_map: dict[str, dict[str, str | None]]
    edge_map: dict[str, dict[str, str | None]]
    revision: int
