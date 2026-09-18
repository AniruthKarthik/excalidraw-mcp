"""Validated document persistence in an explicitly configured directory."""
import json
import os
import re
import stat
import uuid
from contextlib import contextmanager

from config import max_scene_bytes, scene_directory
from excalidraw.errors import SceneError
from excalidraw.document import normalize_document, serialize_document
from excalidraw.models import new_document


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
    payload = serialize_document(document)
    payload_size = len(payload.encode("utf-8"))
    size_limit = max_scene_bytes()
    if payload_size > size_limit:
        raise SceneError(f"Scene exceeds the configured limit of {size_limit} bytes")
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
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode):
                    raise SceneError("Scene target must be a regular file")
                size_limit = max_scene_bytes()
                if info.st_size > size_limit:
                    raise SceneError(f"Scene exceeds the configured limit of {size_limit} bytes")
                document = json.load(stream)
        return normalize_document(document)
    except FileNotFoundError as exc:
        raise SceneError(f"Scene '{name}' not found") from exc
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise SceneError("Scene is not a valid UTF-8 JSON document") from exc
    except OSError as exc:
        raise SceneError(f"Could not load scene: {exc.strerror}") from exc


def list_scenes():
    try:
        with _directory() as (_, directory_fd):
            names = []
            for filename in os.listdir(directory_fd):
                if not filename.endswith(".excalidraw"):
                    continue
                if _check_target(directory_fd, filename):
                    names.append(filename.removesuffix(".excalidraw"))
            return sorted(names)
    except FileNotFoundError:
        return []
    except OSError as exc:
        raise SceneError(f"Could not list scenes: {exc.strerror}") from exc
