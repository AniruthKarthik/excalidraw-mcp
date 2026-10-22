"""Image preview renderer for Excalidraw scenes.

Renders active canvas elements into a PNG image preview suitable for inline
display in MCP clients (Claude Desktop, Cursor, etc.).
"""

import io
import math
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def _parse_color(
    color_str: str | None, opacity: int | float = 100
) -> tuple[int, int, int, int]:
    """Parse Excalidraw color string into an RGBA 4-tuple."""
    if not color_str or color_str.strip().lower() == "transparent":
        return (0, 0, 0, 0)

    color_str = color_str.strip()
    alpha_mul = max(0.0, min(1.0, float(opacity) / 100.0))

    if color_str.startswith("#"):
        hex_val = color_str.lstrip("#")
        if len(hex_val) == 3:
            r = int(hex_val[0] * 2, 16)
            g = int(hex_val[1] * 2, 16)
            b = int(hex_val[2] * 2, 16)
            return (r, g, b, int(255 * alpha_mul))
        if len(hex_val) == 4:
            r = int(hex_val[0] * 2, 16)
            g = int(hex_val[1] * 2, 16)
            b = int(hex_val[2] * 2, 16)
            a = int(hex_val[3] * 2, 16)
            return (r, g, b, int(a * alpha_mul))
        if len(hex_val) == 6:
            r = int(hex_val[0:2], 16)
            g = int(hex_val[2:4], 16)
            b = int(hex_val[4:6], 16)
            return (r, g, b, int(255 * alpha_mul))
        if len(hex_val) == 8:
            r = int(hex_val[0:2], 16)
            g = int(hex_val[2:4], 16)
            b = int(hex_val[4:6], 16)
            orig_a = int(hex_val[6:8], 16)
            return (r, g, b, int(orig_a * alpha_mul))

    # Named fallback or dark default
    if color_str.lower() in ("white", "#fff", "#ffffff"):
        return (255, 255, 255, int(255 * alpha_mul))
    if color_str.lower() in ("black", "#000", "#000000"):
        return (0, 0, 0, int(255 * alpha_mul))
    return (30, 30, 30, int(255 * alpha_mul))


def _compute_bounds(
    elements: list[dict[str, Any]],
    default_box: tuple[float, float, float, float] = (0.0, 0.0, 600.0, 400.0),
) -> tuple[float, float, float, float]:
    """Compute the world-coordinate bounding box of active elements."""
    if not elements:
        return default_box

    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")

    for el in elements:
        x, y = float(el.get("x", 0)), float(el.get("y", 0))
        w, h = float(el.get("width", 0)), float(el.get("height", 0))
        etype = el.get("type")

        if etype == "arrow":
            points = el.get("points") or [[0.0, 0.0], [w, h]]
            for pt in points:
                px = x + float(pt[0])
                py = y + float(pt[1])
                min_x = min(min_x, px)
                min_y = min(min_y, py)
                max_x = max(max_x, px)
                max_y = max(max_y, py)
        else:
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x + w)
            max_y = max(max_y, y + h)

    if min_x == float("inf"):
        return default_box

    if max_x - min_x < 20:
        max_x = min_x + 100
    if max_y - min_y < 20:
        max_y = min_y + 100

    return min_x, min_y, max_x, max_y


def _draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    p1: tuple[float, float],
    p2: tuple[float, float],
    fill: tuple[int, int, int, int],
    width: int = 1,
    dash_len: float = 8.0,
    gap_len: float = 5.0,
):
    """Draw a 2D line segment with dashes."""
    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1
    dist = math.hypot(dx, dy)
    if dist < 1e-4:
        return

    ux = dx / dist
    uy = dy / dist
    cur = 0.0

    while cur < dist:
        seg_end = min(cur + dash_len, dist)
        sp = (x1 + cur * ux, y1 + cur * uy)
        ep = (x1 + seg_end * ux, y1 + seg_end * uy)
        draw.line([sp, ep], fill=fill, width=width)
        cur += dash_len + gap_len


def _draw_arrowhead(
    draw: ImageDraw.ImageDraw,
    tip: tuple[float, float],
    prev_pt: tuple[float, float],
    fill: tuple[int, int, int, int],
    size: float = 14.0,
    angle_deg: float = 26.0,
):
    """Draw a classic filled arrowhead pointing at tip."""
    tx, ty = tip
    px, py = prev_pt
    dx = tx - px
    dy = ty - py
    length = math.hypot(dx, dy)
    if length < 1e-4:
        return

    ux = dx / length
    uy = dy / length

    angle_rad = math.radians(angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    lx = tx - size * (ux * cos_a - uy * sin_a)
    ly = ty - size * (uy * cos_a + ux * sin_a)
    rx = tx - size * (ux * cos_a + uy * sin_a)
    ry = ty - size * (uy * cos_a - ux * sin_a)

    draw.polygon([(tx, ty), (lx, ly), (rx, ry)], fill=fill)


def _get_font(size: int) -> ImageFont.ImageFont:
    """Load default scalable font with requested pixel size."""
    try:
        return ImageFont.load_default(size=max(8, size))
    except Exception:
        return ImageFont.load_default()


def render_scene_to_png(
    document: dict[str, Any], scale: float = 1.0, padding: int = 40
) -> bytes:
    """Render an Excalidraw document dictionary to PNG image bytes.

    Args:
        document: Standard Excalidraw schema dictionary.
        scale: Resolution multiplier (0.25 to 4.0).
        padding: Padding in pixels around bounding box.

    Returns:
        PNG binary data.
    """
    scale = max(0.25, min(4.0, float(scale)))
    padding = max(0, min(200, int(padding)))

    elements = [
        el for el in document.get("elements", []) if not el.get("isDeleted")
    ]
    app_state = document.get("appState") or {}
    bg_color_hex = app_state.get("viewBackgroundColor", "#ffffff")
    bg_color = _parse_color(bg_color_hex, 100)
    if bg_color[3] == 0:
        bg_color = (255, 255, 255, 255)

    min_x, min_y, max_x, max_y = _compute_bounds(elements)

    world_w = max_x - min_x + 2 * padding
    world_h = max_y - min_y + 2 * padding
    img_w = max(100, min(4096, int(world_w * scale)))
    img_h = max(100, min(4096, int(world_h * scale)))

    image = Image.new("RGBA", (img_w, img_h), bg_color)
    draw = ImageDraw.Draw(image)

    def tx(wx: float) -> float:
        return (wx - min_x + padding) * scale

    def ty(wy: float) -> float:
        return (wy - min_y + padding) * scale

    if not elements:
        # Empty scene watermark
        font = _get_font(int(18 * scale))
        draw.text(
            (img_w / 2, img_h / 2),
            "(Empty Excalidraw Canvas)",
            fill=(160, 160, 160, 255),
            font=font,
            anchor="mm",
        )
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()

    # Partition elements by rendering phase:
    # 1. Frames (background container)
    # 2. Geometric Shapes (rectangles, diamonds, ellipses)
    # 3. Connectors & Arrows
    # 4. Text & Labels (top layer)
    frames = []
    shapes = []
    arrows = []
    texts = []

    for el in elements:
        etype = el.get("type")
        if etype == "frame":
            frames.append(el)
        elif etype in ("rectangle", "diamond", "ellipse"):
            shapes.append(el)
        elif etype == "arrow":
            arrows.append(el)
        elif etype == "text":
            texts.append(el)

    # 1. Render Frames
    for f in frames:
        fx = tx(f.get("x", 0))
        fy = ty(f.get("y", 0))
        fw = f.get("width", 0) * scale
        fh = f.get("height", 0) * scale
        frame_color = (180, 180, 190, 255)

        # Dashed border
        _draw_dashed_line(draw, (fx, fy), (fx + fw, fy), frame_color, width=2)
        _draw_dashed_line(
            draw, (fx + fw, fy), (fx + fw, fy + fh), frame_color, width=2
        )
        _draw_dashed_line(
            draw, (fx + fw, fy + fh), (fx, fy + fh), frame_color, width=2
        )
        _draw_dashed_line(draw, (fx, fy + fh), (fx, fy), frame_color, width=2)

        # Frame name badge
        name = f.get("name") or "Frame"
        f_font = _get_font(int(12 * scale))
        draw.text(
            (fx + 6 * scale, fy + 4 * scale),
            name,
            fill=(110, 110, 120, 255),
            font=f_font,
        )

    # 2. Render Shapes
    for s in shapes:
        sx = tx(s.get("x", 0))
        sy = ty(s.get("y", 0))
        sw = s.get("width", 0) * scale
        sh = s.get("height", 0) * scale
        stype = s.get("type")

        opacity = s.get("opacity", 100)
        stroke_color = _parse_color(s.get("strokeColor", "#1e1e1e"), opacity)
        bg_fill = _parse_color(s.get("backgroundColor", "transparent"), opacity)
        stroke_w = max(1, int(s.get("strokeWidth", 1) * scale))

        if stype == "rectangle":
            roundness = s.get("roundness")
            radius = 0
            if isinstance(roundness, dict):
                rtype = roundness.get("type")
                if rtype == 3:  # adaptive
                    radius = max(
                        4, min(int(min(sw, sh) * 0.15), int(32 * scale))
                    )
                elif rtype == 2:  # round
                    radius = max(
                        8, min(int(min(sw, sh) * 0.25), int(48 * scale))
                    )

            fill_val = bg_fill if bg_fill[3] > 0 else None
            outline_val = stroke_color if stroke_color[3] > 0 else None

            if radius > 0:
                draw.rounded_rectangle(
                    [sx, sy, sx + sw, sy + sh],
                    radius=radius,
                    fill=fill_val,
                    outline=outline_val,
                    width=stroke_w,
                )
            else:
                draw.rectangle(
                    [sx, sy, sx + sw, sy + sh],
                    fill=fill_val,
                    outline=outline_val,
                    width=stroke_w,
                )

        elif stype == "ellipse":
            fill_val = bg_fill if bg_fill[3] > 0 else None
            outline_val = stroke_color if stroke_color[3] > 0 else None
            draw.ellipse(
                [sx, sy, sx + sw, sy + sh],
                fill=fill_val,
                outline=outline_val,
                width=stroke_w,
            )

        elif stype == "diamond":
            top = (sx + sw / 2, sy)
            right = (sx + sw, sy + sh / 2)
            bottom = (sx + sw / 2, sy + sh)
            left = (sx, sy + sh / 2)
            pts = [top, right, bottom, left]

            if bg_fill[3] > 0:
                draw.polygon(pts, fill=bg_fill)
            if stroke_color[3] > 0:
                draw.polygon(pts, outline=stroke_color, width=stroke_w)

    # 3. Render Arrows
    for a in arrows:
        ax = a.get("x", 0)
        ay = a.get("y", 0)
        points = a.get("points") or [[0.0, 0.0], [50.0, 50.0]]
        opacity = a.get("opacity", 100)
        stroke_color = _parse_color(a.get("strokeColor", "#1e1e1e"), opacity)
        stroke_w = max(1, int(a.get("strokeWidth", 2) * scale))

        screen_pts = [(tx(ax + pt[0]), ty(ay + pt[1])) for pt in points]
        if len(screen_pts) >= 2:
            draw.line(screen_pts, fill=stroke_color, width=stroke_w)

            # Arrowhead at end
            if a.get("endArrowhead", "arrow") == "arrow":
                _draw_arrowhead(
                    draw,
                    screen_pts[-1],
                    screen_pts[-2],
                    stroke_color,
                    size=max(10.0, 14.0 * scale),
                )
            # Arrowhead at start
            if a.get("startArrowhead") == "arrow":
                _draw_arrowhead(
                    draw,
                    screen_pts[0],
                    screen_pts[1],
                    stroke_color,
                    size=max(10.0, 14.0 * scale),
                )

    # 4. Render Text & Labels
    for t in texts:
        text_content = t.get("text", "")
        if not text_content:
            continue
        px = tx(t.get("x", 0))
        py = ty(t.get("y", 0))
        font_size = int(t.get("fontSize", 20) * scale)
        font = _get_font(font_size)
        opacity = t.get("opacity", 100)
        stroke_color = _parse_color(t.get("strokeColor", "#1e1e1e"), opacity)
        text_align = t.get("textAlign", "left")

        draw.text(
            (px, py),
            text_content,
            fill=stroke_color,
            font=font,
            align=text_align,
        )

    # Save to buffer and return bytes
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
