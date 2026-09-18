"""One process-local scene with validated, serialized commits and detached reads."""
import random
import time
from copy import deepcopy
from threading import RLock
from typing import Callable, TypeVar

from config import history_limit
from excalidraw.errors import SceneError
from excalidraw.document import normalize_document
from excalidraw.models import SceneDocument, new_document, validate_document

T = TypeVar("T")


class SceneState:
    def __init__(self, max_history=None):
        self._lock = RLock()
        self._document = new_document()
        self._index = {}
        self._revision = 0
        self._editing = False
        self._max_history = history_limit() if max_history is None else max_history
        if not 1 <= self._max_history <= 100:
            raise ValueError("max_history must be between 1 and 100")
        self._history = []

    @property
    def revision(self):
        with self._lock:
            return self._revision

    @property
    def elements(self):
        return self.all()

    def document(self):
        with self._lock:
            return deepcopy(self._document)

    def get(self, element_id):
        with self._lock:
            return deepcopy(self._index.get(element_id))

    def all(self):
        with self._lock:
            return deepcopy(self._document["elements"])

    @property
    def history_depth(self):
        with self._lock:
            return len(self._history)

    def _remember(self, document):
        self._history.append(deepcopy(document))
        del self._history[:-self._max_history]

    def _commit(self, document, previous, remember=True):
        replacement = normalize_document(document)
        if replacement == previous:
            return False
        old = {el["id"]: el for el in previous["elements"]}
        for el in replacement["elements"]:
            before = old.get(el["id"])
            if before != el:
                version = before.get("version", 0) if before else 0
                updated = before.get("updated", 0) if before else 0
                el["version"] = (version if type(version) is int and version >= 0 else 0) + 1
                el["versionNonce"] = random.randrange(1, 2**31)
                el["updated"] = max(
                    time.time_ns() // 1_000_000,
                    (updated if type(updated) is int else 0) + 1,
                )
        if remember:
            self._remember(previous)
        self._document = replacement
        self._index = {el["id"]: el for el in replacement["elements"]}
        self._revision += 1
        return True

    def replace(self, document, expected_revision=None):
        with self._lock:
            if self._editing:
                raise SceneError("Nested scene mutations are not supported")
            if expected_revision is not None and self._revision != expected_revision:
                raise SceneError("Scene changed while replacement was being prepared; retry the operation")
            replacement = normalize_document(document)
            if replacement == self._document:
                return
            self._remember(self._document)
            self._document = replacement
            self._index = {el["id"]: el for el in replacement["elements"]}
            self._revision += 1

    def apply(self, operation: Callable[[SceneDocument], T]) -> T:
        """Apply a callback to a private draft. Exceptions roll back all edits."""
        with self._lock:
            if self._editing:
                raise SceneError("Nested scene mutations are not supported")
            self._editing = True
            try:
                draft = deepcopy(self._document)
                result = deepcopy(operation(draft))
                self._commit(draft, self._document)
                return result
            finally:
                self._editing = False

    def add_many(self, elements):
        incoming = validate_document(new_document(elements))["elements"]
        def append(document):
            document["elements"].extend(incoming)
            return [el["id"] for el in incoming]
        return self.apply(append)

    def add(self, element):
        return self.add_many([element])[0]

    def clear(self):
        with self._lock:
            if self._editing:
                raise SceneError("Nested scene mutations are not supported")
            self._commit(new_document(), self._document)

    def undo(self):
        with self._lock:
            if self._editing:
                raise SceneError("Nested scene mutations are not supported")
            if not self._history:
                raise SceneError("Nothing to undo")
            previous = self._history.pop()
            self._document = normalize_document(previous)
            self._index = {el["id"]: el for el in self._document["elements"]}
            self._revision += 1
            return {"status": "undone", "revision": self._revision,
                    "history_depth": len(self._history)}
