from copy import deepcopy

from excalidraw.scene import new_document, validate_document


class SceneState:
    def __init__(self):
        self._document = new_document()

    @property
    def elements(self):
        return self._document["elements"]

    def document(self):
        return deepcopy(self._document)

    def replace(self, document):
        replacement = validate_document(document)
        self._document = replacement

    def add(self, element):
        element_id = element["id"]
        self.elements.append(element)
        return element_id

    def clear(self):
        self._document = new_document()

    def get(self, element_id):
        for el in self.elements:
            if el["id"] == element_id:
                return el
        return None

    def delete(self, element_id):
        self._document["elements"] = [el for el in self.elements if el["id"] != element_id]

    def all(self):
        return self.elements
