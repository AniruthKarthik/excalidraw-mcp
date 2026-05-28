def horizontal_layout(nodes):
    """Auto position nodes horizontally"""

    positioned = []

    start_x = 100
    y = 200

    gap = 300

    for i, node in enumerate(nodes):
        positioned.append({
            "label": node,
            "x": start_x + (i * gap),
            "y": y,
            "w": 200,
            "h": 100,
        })

    return positioned