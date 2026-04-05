import unittest

from tree_model import TreeModel


class TreeModelTests(unittest.TestCase):
    def test_full_name_and_add_child(self) -> None:
        root = TreeModel(name="root")
        a = TreeModel(name="a")
        b = TreeModel(name="b")

        root.add_child(a)
        a.add_child(b)

        self.assertIs(a.parent, root)
        self.assertIs(b.parent, a)

        self.assertEqual(root.full_name, "root")
        self.assertEqual(a.full_name, "root.a")
        self.assertEqual(b.full_name, "root.a.b")

    def test_exists_child_recursive(self) -> None:
        root = TreeModel(name="root")
        a = TreeModel(name="a")
        b = TreeModel(name="b")

        root.add_child(a)
        a.add_child(b)

        self.assertTrue(root.exists_child("a"))
        self.assertFalse(root.exists_child("b"))
        self.assertTrue(root.exists_child("a.b", recursive=True))
        self.assertFalse(root.exists_child("missing", recursive=True))

    def test_get_child_recursive(self) -> None:
        root = TreeModel(name="root")
        a = TreeModel(name="a")
        b = TreeModel(name="b")

        root.add_child(a)
        a.add_child(b)

        self.assertIs(root.get_child("a"), a)
        self.assertIs(root.get_child("a.b", recursive=True), b)

    def test_find_child_returns_none_when_missing(self) -> None:
        root = TreeModel(name="root")
        a = TreeModel(name="a")

        root.add_child(a)

        self.assertIsNone(root.find_child("missing"))
        self.assertIsNone(root.find_child("a.missing", recursive=True))

    def test_get_child_raises_when_missing(self) -> None:
        root = TreeModel(name="root")

        with self.assertRaises(ValueError):
            root.get_child("missing")

    def test_delete_child_removes_parent_handle(self) -> None:
        root = TreeModel(name="root")
        child = TreeModel(name="child")

        root.add_child(child)
        self.assertTrue(root.exists_child("child"))

        child.delete()

        self.assertFalse(root.exists_child("child"))
        self.assertIsNone(child.parent)

    def test_delete_parent_deletes_descendants(self) -> None:
        root = TreeModel(name="root")
        a = TreeModel(name="a")
        b = TreeModel(name="b")

        root.add_child(a)
        a.add_child(b)

        root.delete()

        self.assertIsNone(root.parent)
        self.assertIsNone(a.parent)
        self.assertIsNone(b.parent)
        self.assertEqual(len(list(root)), 0)

    def test_add_child_rejects_separator_in_name(self) -> None:
        root = TreeModel(name="root")
        bad = TreeModel(name="a.b")

        with self.assertRaises(ValueError):
            root.add_child(bad)

    def test_add_child_rejects_existing_parent(self) -> None:
        root1 = TreeModel(name="root1")
        root2 = TreeModel(name="root2")
        child = TreeModel(name="child")

        root1.add_child(child)

        with self.assertRaises(ValueError):
            root2.add_child(child)


if __name__ == "__main__":
    unittest.main()