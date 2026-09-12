"""Validated document persistence in an explicitly configured directory."""
import json
import math
import os
import re
import stat
import uuid
from contextlib import contextmanager
from copy import deepcopy

from config import scene_directory
from excalidraw.errors import SceneError


def new_document(elements=None):
    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": [] if elements is None else elements,
        "appState": {},
        "files": {},
    }


def _finite_number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def validate_document(document):
    """Validate structural invariants while retaining unfamiliar imported fields."""
    if not isinstance(document, dict) or document.get("type") != "excalidraw":
        raise SceneError("Expected an Excalidraw document")
    if type(document.get("version")) is not int or document["version"] != 2:
        raise SceneError("Only Excalidraw document version 2 is supported")
    if not isinstance(document.get("elements"), list):
        raise SceneError("Document elements must be a list")
    for field in ("appState", "files"):
        if not isinstance(document.get(field, {}), dict):
            raise SceneError(f"Document {field} must be an object")
    ids = set()
    for element in document["elements"]:
        if not isinstance(element, dict):
            raise SceneError("Each element must be an object")
        element_id = element.get("id")
        if not isinstance(element_id, str) or not element_id.strip() or element_id in ids:
            raise SceneError("Element IDs must be nonempty, unique strings")
        ids.add(element_id)
        if not isinstance(element.get("type"), str) or not element["type"].strip():
            raise SceneError(f"Element {element_id} needs a type")
        for field in ("x", "y", "width", "height"):
            if field in ("width", "height") and field not in element:
                continue
            value = element.get(field)
            if not _finite_number(value):
                raise SceneError(f"Element {element_id} needs a finite {field}")
            if field in ("width", "height") and value < 0:
                raise SceneError(f"Element {element_id} has negative {field}")
    try:
        json.dumps(document, allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise SceneError("Document must contain finite JSON data") from exc
    result = deepcopy(document)
    result.setdefault("appState", {})
    result.setdefault("files", {})
    return result


def _filename(name):
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", name):
        raise SceneError(
            "Scene name must be 1–128 letters, digits, underscores or hyphens, "
            "starting with a letter or digit; omit the extension"
        )
    return f"{name}.excalidraw"


@contextmanager
def _directory(create=False):
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise SceneError("Safe scene storage currently requires Linux or macOS")
    # The configured root is trusted. Anchor operations to its open descriptor
    # so replacement of a directory path cannot redirect an in-flight operation.
    root = scene_directory().resolve()
    if create:
        root.mkdir(parents=True, exist_ok=True)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        yield root, fd
    finally:
        os.close(fd)


def _check_target(fd, filename):
    try:
        info = os.stat(filename, dir_fd=fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(info.st_mode):
        raise SceneError("Scene target must be a regular file, not a symlink or directory")
    return True


def save_scene(name, document, overwrite=False):
    filename = _filename(name)
    document = validate_document(document)
    payload = json.dumps(document, ensure_ascii=False, allow_nan=False, indent=2)
    try:
        with _directory(create=True) as (root, directory_fd):
            if _check_target(directory_fd, filename) and not overwrite:
                raise SceneError("Scene already exists; use overwrite=true to replace it")
            temporary = f".scene-{uuid.uuid4().hex}.tmp"
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory_fd)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                if overwrite:
                    _check_target(directory_fd, filename)
                    os.replace(temporary, filename, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
                else:
                    # Publishing with a hard link atomically refuses an existing
                    # destination, even when another save wins the race.
                    os.link(temporary, filename, src_dir_fd=directory_fd, dst_dir_fd=directory_fd, follow_symlinks=False)
            finally:
                try:
                    os.unlink(temporary, dir_fd=directory_fd)
                except FileNotFoundError:
                    pass
            return str(root / filename)
    except FileExistsError as exc:
        raise SceneError("Scene already exists; use overwrite=true to replace it") from exc
    except UnicodeError as exc:
        raise SceneError("Scene contains text that cannot be encoded as UTF-8") from exc
    except OSError as exc:
        raise SceneError(f"Could not save scene: {exc.strerror}") from exc


def load_scene(name):
    filename = _filename(name)
    try:
        with _directory() as (_, directory_fd):
            if not _check_target(directory_fd, filename):
                raise SceneError(f"Scene '{name}' not found")
            fd = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
            with os.fdopen(fd, "r", encoding="utf-8") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise SceneError("Scene target must be a regular file")
                document = json.load(stream)
        return validate_document(document)
    except FileNotFoundError as exc:
        raise SceneError(f"Scene '{name}' not found") from exc
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise SceneError("Scene is not a valid UTF-8 JSON document") from exc
    except OSError as exc:
        raise SceneError(f"Could not load scene: {exc.strerror}") from exc
