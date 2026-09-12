"""Storage configuration with no import-time filesystem writes."""
import os
from pathlib import Path


def scene_directory():
    configured = os.environ.get("EXCALIDRAW_SCENE_DIR")
    root = (
        Path(configured).expanduser()
        if configured else Path(__file__).resolve().parent / "scenes"
    )
    if not root.is_absolute():
        raise ValueError("EXCALIDRAW_SCENE_DIR must be an absolute path")
    return root
