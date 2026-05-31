import json
import urllib.parse
from pathlib import Path

SCENE_DIR = Path("scenes")
SCENE_DIR.mkdir(exist_ok=True)


def save_scene(name, elements):
    scene = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {},
        "files": {},
    }

    path = SCENE_DIR / f"{name}.excalidraw"

    with open(path, "w") as f:
        json.dump(scene, f, indent=2)

    return str(path)


def load_scene(name):
    path = SCENE_DIR / f"{name}.excalidraw"
    if not path.exists():
        return None

    with open(path) as f:
        scene = json.load(f)

    return scene.get("elements", [])


def open_scene(elements):
    scene = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {},
    }

    encoded = urllib.parse.quote(json.dumps(scene))

    url = f"https://excalidraw.com/#json={encoded}"
    return url
