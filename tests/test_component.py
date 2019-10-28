import unittest

from system import Component, SystemDefinitionError

class ComponentTest(unittest.TestCase):
    def setUp(self):
        self.circular_transitions = [
                ("first", "label1", "second"),
                ("second", "label2", "first"),
                ]
        self.same_label_transitions = [
                ("first", "label", "second"),
                ("second", "label", "first"),
                ]

    def test_transitions_by_label(self):
        component = Component("Test Component", "first",
                self.circular_transitions)
        self.assertEqual(component.edge_with_label("label1"),
                ("first", "second"))
        self.assertEqual(component.edge_with_label("label2"),
                ("second", "first"))

    def test_inconsistency_detections(self):
        with self.assertRaises(SystemDefinitionError):
            Component("Test Component", "initial", self.circular_transitions)
        with self.assertRaises(SystemDefinitionError):
            Component("Test Component", "first", self.same_label_transitions)


if __name__ == '__main__':
    unittest.main()
