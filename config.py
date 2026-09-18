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


def history_limit():
    raw = os.environ.get("EXCALIDRAW_HISTORY_LIMIT", "20")
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError("EXCALIDRAW_HISTORY_LIMIT must be an integer") from exc
    if not 1 <= value <= 100:
        raise ValueError("EXCALIDRAW_HISTORY_LIMIT must be between 1 and 100")
    return value
