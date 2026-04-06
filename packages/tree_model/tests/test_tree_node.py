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

    def test_len_and_iter_direct_children(self) -> None:
        root = TreeModel(name="root")
        a = TreeModel(name="a")
        b = TreeModel(name="b")
        root.add_child(a)
        root.add_child(b)

        self.assertEqual(len(root), 2)
        self.assertEqual(list(root), [a, b])

    def test_exists_non_recursive_and_recursive(self) -> None:
        root = TreeModel(name="root")
        a = TreeModel(name="a")
        b = TreeModel(name="b")

        root.add_child(a)
        a.add_child(b)

        self.assertTrue(root.exists_child(lambda n: n.name == "a"))
        self.assertFalse(root.exists_child(lambda n: n.name == "b"))
        self.assertTrue(root.exists_child(lambda n: n.name == "b", recursive=True))
        self.assertFalse(root.exists_child(lambda n: n.name == "missing", recursive=True))

    def test_find_by_name(self) -> None:
        root = TreeModel(name="root")
        a = TreeModel(name="a")
        b = TreeModel(name="b")
        root.add_child(a)
        a.add_child(b)

        self.assertIs(root.find_child_by_name("a"), a)
        self.assertIsNone(root.find_child_by_name("b"))
        self.assertIs(root.find_child_by_name("b", recursive=True), b)

    def test_get_raises_when_missing(self) -> None:
        root = TreeModel(name="root")

        with self.assertRaises(ValueError) as ctx:
            root.get_child(lambda n: n.name == "missing")
        self.assertIn("未找到", str(ctx.exception))

    def test_get_recursive(self) -> None:
        root = TreeModel(name="root")
        a = TreeModel(name="a")
        b = TreeModel(name="b")
        root.add_child(a)
        a.add_child(b)

        self.assertIs(root.get_child(lambda n: n.name == "a"), a)
        self.assertIs(root.get_child(lambda n: n.name == "b", recursive=True), b)

    def test_find_returns_none_when_missing(self) -> None:
        root = TreeModel(name="root")
        a = TreeModel(name="a")
        root.add_child(a)

        self.assertIsNone(root.find_child_by_name("missing"))
        self.assertIsNone(root.find_child_by_name("missing", recursive=True))

    def test_filter_shallow_and_recursive(self) -> None:
        root = TreeModel(name="root")
        a = TreeModel(name="a")
        b = TreeModel(name="b")
        c = TreeModel(name="b")
        root.add_child(a)
        a.add_child(b)
        root.add_child(c)

        self.assertEqual(root.filter_child(lambda n: n.name == "b"), [c])
        self.assertEqual(root.filter_child(lambda n: n.name == "b", recursive=True), [b, c])

    def test_delete_child_removes_from_parent(self) -> None:
        root = TreeModel(name="root")
        child = TreeModel(name="child")

        root.add_child(child)
        self.assertTrue(root.exists_child(lambda n: n.name == "child"))

        child.delete()

        self.assertFalse(root.exists_child(lambda n: n.name == "child"))
        self.assertIsNone(child.parent)
        self.assertEqual(len(root), 0)

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

    def test_add_child_rejects_same_child_twice(self) -> None:
        root = TreeModel(name="root")
        child = TreeModel(name="child")
        root.add_child(child)

        with self.assertRaises(ValueError) as ctx:
            root.add_child(child)
        self.assertIn("parent", str(ctx.exception))

    def test_on_delete_callback_runs_when_node_deleted(self) -> None:
        root = TreeModel(name="root")
        child = TreeModel(name="child")
        root.add_child(child)

        called: list[str] = []

        def mark() -> None:
            called.append("x")

        child.on_delete(mark)
        child.delete()

        self.assertEqual(called, ["x"])
        self.assertEqual(len(root), 0)


if __name__ == "__main__":
    unittest.main()
