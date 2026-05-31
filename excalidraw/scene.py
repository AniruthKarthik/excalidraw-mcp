import json
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
    """Generate a URL to view the scene in Excalidraw.

    Uses lz-string compression (same algorithm Excalidraw uses natively)
    to produce URLs ~70% shorter than the raw ``#json=`` approach.
    """
    scene = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {},
        "files": {},
    }

    raw = json.dumps(scene, separators=(",", ":"))

    try:
        from lzstring import LZString

        lz = LZString()
        compressed = lz.compressToEncodedURIComponent(raw)
        url = f"https://excalidraw.com/#{compressed}"
    except ImportError:
        import urllib.parse

        encoded = urllib.parse.quote(raw)
        url = f"https://excalidraw.com/#json={encoded}"

    return url
