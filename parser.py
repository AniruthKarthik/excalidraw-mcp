import re


SHAPE_ALIASES = {
    "box": "rectangle",
    "rect": "rectangle",
    "rectangle": "rectangle",
    "circle": "ellipse",
    "ellipse": "ellipse",
    "diamond": "diamond",
}


def parse_architecture(prompt: str):
    """Parse a loose architecture prompt into labeled shape nodes."""

    parts = [
        part.strip()
        for part in re.split(r"[\n,]+", prompt)
        if part.strip()
    ]

    nodes = []

    for part in parts:
        cleaned = part.lstrip("-* ").strip()
        shape = "rectangle"
        label = cleaned

        if ":" in cleaned:
            prefix, suffix = cleaned.split(":", 1)
            candidate = prefix.strip().lower()
            if candidate in SHAPE_ALIASES:
                shape = SHAPE_ALIASES[candidate]
                label = suffix.strip()
        else:
            words = cleaned.split(None, 1)
            if len(words) > 1 and words[0].lower() in SHAPE_ALIASES:
                shape = SHAPE_ALIASES[words[0].lower()]
                label = words[1].strip()

        nodes.append({
            "label": label,
            "shape": shape,
        })

    return nodes
