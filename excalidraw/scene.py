import json
import urllib.parse
import webbrowser
from pathlib import Path

SCENE_DIR = Path("scenes")
SCENE_DIR.mkdir(exist_ok=True)


def save_scene(name, elements):
    scene = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appstate": {},
        "files": {},
    }

    path = SCENE_DIR / f"{name}.excalidraw"

    with open(path, "w") as f:
        json.dump(scene, f, indent=2)

    return str(path)


def open_scene(elements):
    scene = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appstate": {},
        "files": {},
    }

    encoded = urllib.parse.quote(json.dumps(scene))

    url = f"https://excalidraw.com/#json={encoded}"
    webbrowser.open(url)

    return "opened in browser"
