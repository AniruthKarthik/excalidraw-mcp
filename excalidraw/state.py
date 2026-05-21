class SceneState:
    def __init__(self):
        self.elements = []

    def add(self, element):
        self.elements.append(element)
        return element["id"]

    def clear(self):
        self.elements = []

    def get(self, element_id):
        for el in self.elements:
            if el["id"] == element_id:
                return el
        return None

    def delete(self, element_id):
        self.elements = [el for el in self.elements if el["id"] != element_id]
