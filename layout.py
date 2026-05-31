def shape_dimensions(shape: str, label: str):
    label_width = max(120, len(label) * 12 + 40)

    if shape == "ellipse":
        size = max(120, label_width)
        return size, size

    if shape == "diamond":
        return max(180, label_width), 110

    return max(200, label_width), 100


def horizontal_layout(nodes):
    """Auto position nodes horizontally."""

    positioned = []

    start_x = 100
    y = 200
    gap = 300

    for index, node in enumerate(nodes):
        width, height = shape_dimensions(node["shape"], node["label"])
        positioned.append({
            "label": node["label"],
            "shape": node["shape"],
            "x": start_x + (index * gap),
            "y": y,
            "w": width,
            "h": height,
        })

    return positioned
