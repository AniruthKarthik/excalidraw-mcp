import json
from pathlib import Path

SCENE_DIR = Path("scenes")
SCENE_DIR.mkdir(exist_ok=True)


def save_scene(name, elements):
    scene = {
        "type": "excalidraw",
        "version": 2,
        "elements": elements,
    }

    path = SCENE_DIR / f"{name}.excalidraw"

    with open(path, "w") as f:
        json.dump(scene, f, indent=2)

    return str(path)
