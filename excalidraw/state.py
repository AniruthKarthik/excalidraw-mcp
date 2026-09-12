"""One process-local scene with validated, serialized commits and detached reads."""
import random
import time
from copy import deepcopy
from threading import RLock
from typing import Callable, TypeVar

from excalidraw.errors import SceneError
from excalidraw.models import SceneDocument, new_document, normalize_relationships, validate_document

T = TypeVar("T")


class SceneState:
    def __init__(self):
        self._lock = RLock()
        self._document = new_document()
        self._index = {}
        self._revision = 0
        self._editing = False

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

    def _commit(self, document, previous):
        replacement = validate_document(document)
        normalize_relationships(replacement)
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
        self._document = replacement
        self._index = {el["id"]: el for el in replacement["elements"]}
        self._revision += 1

    def replace(self, document, expected_revision=None):
        with self._lock:
            if self._editing:
                raise SceneError("Nested scene mutations are not supported")
            if expected_revision is not None and self._revision != expected_revision:
                raise SceneError("Scene changed while replacement was being prepared; retry the operation")
            # An imported document keeps its metadata, except elements repaired
            # during relationship normalization, which receive a version bump.
            self._commit(document, validate_document(document))

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
