"""Backend-only Excalidraw v2 import/export contract.

Known elements get explicit defaults; unknown fields and element kinds survive.
This is serialization/validation, not a replacement for Excalidraw's renderer.
"""

import base64
import binascii
import json
from copy import deepcopy

from excalidraw_mcp.elements import DEFAULT_STYLE
from excalidraw_mcp.errors import SceneError
from excalidraw_mcp.models import _finite_number, normalize_relationships, validate_document
from excalidraw_mcp.validation import valid_color

SUPPORTED_TYPES = frozenset({"rectangle", "ellipse", "diamond", "text", "arrow", "frame"})
MIME_TYPE = "application/vnd.excalidraw+json"


def _defaults(element, defaults):
    for key, value in defaults.items():
        element.setdefault(key, deepcopy(value))


def _number(element, field, minimum=None):
    value = element.get(field)
    if not _finite_number(value) or (minimum is not None and value < minimum):
        raise SceneError(f"Element {element['id']} has invalid {field}")


def _normalize_text(el):
    if not isinstance(el.get("text"), str):
        raise SceneError("Text elements require a text string")
    _defaults(
        el,
        {
            "fontSize": 20,
            "fontFamily": 2,
            "containerId": None,
            "originalText": el["text"],
            "autoResize": True,
        },
    )
    _number(el, "fontSize", 1)
    if type(el["fontFamily"]) is not int or el["fontFamily"] < 1:
        raise SceneError("Text fontFamily must be a positive integer")
    if not isinstance(el["originalText"], str) or type(el["autoResize"]) is not bool:
        raise SceneError("Invalid originalText or autoResize on text element")
    lines = el["text"].split("\n")
    # Preserve legacy measured line height when supplied, including older fonts.
    line_height = el.get("height", 0) / (len(lines) * el["fontSize"]) or 1.25
    _defaults(
        el,
        {
            "lineHeight": line_height,
            "textAlign": "center" if el["containerId"] else "left",
            "verticalAlign": "middle" if el["containerId"] else "top",
        },
    )
    _number(el, "lineHeight", 0.01)
    if el["textAlign"] not in ("left", "center", "right") or el[
        "verticalAlign"
    ] not in ("top", "middle", "bottom"):
        raise SceneError("Invalid text alignment")
    el.setdefault("width", max(map(len, lines)) * el["fontSize"] * 0.6)
    el.setdefault("height", len(lines) * el["fontSize"] * el["lineHeight"])


def _normalize_arrow(el):
    points = el.get("points")
    if (
        not isinstance(points, list)
        or len(points) < 2
        or any(
            not isinstance(p, list)
            or len(p) != 2
            or not all(_finite_number(v) for v in p)
            for p in points
        )
    ):
        raise SceneError("Arrow elements require at least two finite points")
    # For unrotated arrows, origin normalization preserves every world point.
    # Keep rotated origins intact because changing their bounds changes the pivot.
    if not el.get("angle", 0):
        ox, oy = points[0]
        el["x"] += ox
        el["y"] += oy
        el["points"] = [[x - ox, y - oy] for x, y in points]
        el["width"] = max(p[0] for p in points) - min(p[0] for p in points)
        el["height"] = max(p[1] for p in points) - min(p[1] for p in points)
    _defaults(
        el,
        {
            "startBinding": None,
            "endBinding": None,
            "startArrowhead": None,
            "endArrowhead": "arrow",
            "lastCommittedPoint": None,
            "elbowed": False,
        },
    )
    for key in ("startBinding", "endBinding"):
        binding = el[key]
        if binding is None:
            continue
        if not isinstance(binding, dict):
            raise SceneError(f"Invalid {key}")
        # v0.18.x uses focus/gap; retain newer fixedPoint/mode fields as well.
        _defaults(binding, {"focus": 0, "gap": 0})
        if (
            not _finite_number(binding["focus"])
            or not -1 <= binding["focus"] <= 1
            or not _finite_number(binding["gap"])
            or binding["gap"] < 0
        ):
            raise SceneError(f"Invalid focus/gap in {key}")
        if "fixedPoint" in binding and binding["fixedPoint"] is not None:
            point = binding["fixedPoint"]
            if (
                not isinstance(point, list)
                or len(point) != 2
                or not all(_finite_number(v) for v in point)
            ):
                raise SceneError(f"Invalid fixedPoint in {key}")


def _validate_image(el, files, validate_data=True):
    file_id = el.get("fileId")
    if not isinstance(file_id, str) or file_id not in files:
        raise SceneError(f"Image {el['id']} has no embedded asset")
    asset = files[file_id]
    if not isinstance(asset, dict) or asset.get("id") != file_id:
        raise SceneError(f"Invalid embedded asset {file_id}")
    mime = asset.get("mimeType")
    data = asset.get("dataURL")
    if not isinstance(mime, str) or not mime.startswith("image/"):
        raise SceneError(f"Invalid image MIME type for {file_id}")
    prefix = f"data:{mime};base64,"
    if not isinstance(data, str) or not data.startswith(prefix):
        raise SceneError(
            f"Image {file_id} must contain embedded base64 data, not a URL"
        )
    if validate_data:
        try:
            if not base64.b64decode(data[len(prefix) :], validate=True):
                raise ValueError("empty asset")
        except (binascii.Error, ValueError) as exc:
            raise SceneError(f"Invalid base64 image data for {file_id}") from exc
    if not _finite_number(asset.get("created")) or asset["created"] < 0:
        raise SceneError(f"Image asset {file_id} needs a creation timestamp")


def normalize_document(document, validate_assets=True):
    result = validate_document(document)
    for el in result["elements"]:
        if el.get("isDeleted"):
            continue
        if el["type"] == "image":
            _validate_image(el, result["files"], validate_data=validate_assets)
            for field in ("width", "height"):
                _number(el, field, 0)
        if el["type"] not in SUPPORTED_TYPES:
            continue
        _defaults(
            el,
            {
                **DEFAULT_STYLE,
                "seed": 1,
                "version": 1,
                "versionNonce": 1,
                "updated": 0,
                "index": None,
                "groupIds": [],
                "frameId": None,
                "boundElements": [],
                "link": None,
                "locked": False,
                "isDeleted": False,
                "roundness": None,
            },
        )
        for key in ("seed", "version", "versionNonce"):
            if type(el[key]) is not int or (key == "version" and el[key] < 1):
                raise SceneError(f"Element {el['id']} has invalid {key}")
        _number(el, "updated", 0)
        if type(el["locked"]) is not bool or type(el["isDeleted"]) is not bool:
            raise SceneError("Element flags must be booleans")
        if not isinstance(el["groupIds"], list) or any(
            not isinstance(group, str) for group in el["groupIds"]
        ):
            raise SceneError("Element groupIds must be a list of strings")
        for key in ("frameId", "index", "link"):
            if el[key] is not None and not isinstance(el[key], str):
                raise SceneError(f"Element {el['id']} has invalid {key}")
        for key in ("strokeColor", "backgroundColor"):
            if not valid_color(el[key]):
                raise SceneError(f"Element {el['id']} has invalid {key}")
        for key, minimum in (
            ("angle", None),
            ("strokeWidth", 0),
            ("roughness", 0),
            ("opacity", 0),
        ):
            _number(el, key, minimum)
        if (
            el["opacity"] > 100
            or el["fillStyle"] not in ("solid", "hachure", "cross-hatch", "zigzag")
            or el["strokeStyle"] not in ("solid", "dashed", "dotted")
        ):
            raise SceneError(f"Element {el['id']} has invalid style")
        if el.get("roundness") is not None:
            r = el["roundness"]
            if not isinstance(r, dict) or type(r.get("type")) is not int or r["type"] not in (1, 2, 3):
                raise SceneError(f"Element {el['id']} has invalid roundness")
        if el["type"] == "text":
            _normalize_text(el)
        elif el["type"] == "arrow":
            _normalize_arrow(el)
        elif el["type"] == "frame":
            if not isinstance(el.get("name", ""), str):
                raise SceneError(f"Frame {el['id']} needs a string name")
            el.setdefault("name", "")
        for field in ("width", "height"):
            _number(el, field, 0)
    normalize_relationships(result)
    return validate_document(result)


def serialize_document(document):
    payload = json.dumps(
        normalize_document(document), ensure_ascii=False, allow_nan=False, indent=2
    )
    try:
        payload.encode("utf-8")
    except UnicodeError as exc:
        raise SceneError("Scene contains text that cannot be encoded as UTF-8") from exc
    return payload
