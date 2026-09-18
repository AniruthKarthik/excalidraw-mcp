import unittest

from parser import parse_architecture


class ParserTests(unittest.TestCase):
    def test_documented_aliases_and_stable_ids(self):
        self.assertEqual(parse_architecture("box: API, circle Database\n- diamond: Decision"), [
            {"id": "node-1", "label": "API", "shape": "rectangle"},
            {"id": "node-2", "label": "Database", "shape": "ellipse"},
            {"id": "node-3", "label": "Decision", "shape": "diamond"},
        ])

    def test_plain_prose_is_one_default_rectangle(self):
        self.assertEqual(parse_architecture("Client -> API -> Database"), [
            {"id": "node-1", "label": "Client -> API -> Database", "shape": "rectangle"},
        ])

    def test_empty_tokens_are_ignored_but_empty_shape_labels_remain_for_validation(self):
        self.assertEqual(parse_architecture(" \n, "), [])
        self.assertEqual(parse_architecture("box:"), [
            {"id": "node-1", "label": "", "shape": "rectangle"},
        ])


if __name__ == "__main__":
    unittest.main()
