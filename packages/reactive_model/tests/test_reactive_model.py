from __future__ import annotations

import unittest

from reactive_model import ComputedModel, DictRefModel, ListRefModel, RefModel
from reactive_model.track import CircularDependencyError


class TestRefModel(unittest.TestCase):
    def test_get_set(self) -> None:
        r = RefModel(10)
        self.assertEqual(r.value, 10)
        r.value = 20
        self.assertEqual(r.value, 20)

    def test_touch_bumps_version(self) -> None:
        r = RefModel(0)
        v0 = r.version
        r.value = 1
        self.assertGreater(r.version, v0)


class TestComputedModel(unittest.TestCase):
    def test_lazy_and_cache(self) -> None:
        calls: list[int] = []

        def expr() -> int:
            calls.append(1)
            return 42

        c = ComputedModel(expr)
        self.assertEqual(calls, [])
        self.assertEqual(c.value, 42)
        self.assertEqual(calls, [1])
        self.assertEqual(c.value, 42)
        self.assertEqual(calls, [1])

    def test_invalidates_when_dep_changes(self) -> None:
        count = RefModel(1)
        double = ComputedModel(lambda: count.value * 2)
        self.assertEqual(double.value, 2)
        v_after_first = double.version
        count.value = 2
        self.assertGreater(count.version, 0)
        self.assertEqual(double.value, 4)
        self.assertGreaterEqual(double.version, v_after_first)

    def test_chained_computed(self) -> None:
        count = RefModel(1)
        double = ComputedModel(lambda: count.value * 2)
        label = ComputedModel(lambda: f"double={double.value}")
        self.assertEqual(label.value, "double=2")
        count.value = 2
        self.assertEqual(double.value, 4)
        self.assertEqual(label.value, "double=4")


class TestCircularDependency(unittest.TestCase):
    def test_mutual_computed_raises(self) -> None:
        a_holder: list[ComputedModel[int] | None] = [None]
        b_holder: list[ComputedModel[int] | None] = [None]

        def a_expr() -> int:
            assert b_holder[0] is not None
            return b_holder[0].value

        def b_expr() -> int:
            assert a_holder[0] is not None
            return a_holder[0].value

        a_holder[0] = ComputedModel(a_expr)
        b_holder[0] = ComputedModel(b_expr)

        with self.assertRaises(CircularDependencyError):
            _ = a_holder[0].value


class TestDictRefModel(unittest.TestCase):
    def test_proxy_mutation_invalidates_computed(self) -> None:
        d = DictRefModel({"x": 1})
        total = ComputedModel(lambda: sum(d.value.values()))
        self.assertEqual(total.value, 1)
        d.value["x"] = 10
        self.assertEqual(total.value, 10)

    def test_replace_whole_dict(self) -> None:
        d = DictRefModel({"a": 1})
        keys = ComputedModel(lambda: sorted(d.value.keys()))
        self.assertEqual(keys.value, ["a"])
        d.value = {"b": 2}
        self.assertEqual(keys.value, ["b"])


class TestListRefModel(unittest.TestCase):
    def test_proxy_mutation_invalidates_computed(self) -> None:
        lst = ListRefModel([1, 2, 3])
        s = ComputedModel(lambda: sum(lst.value))
        self.assertEqual(s.value, 6)
        lst.value.append(4)
        self.assertEqual(s.value, 10)

    def test_replace_whole_list(self) -> None:
        lst = ListRefModel([1])
        length = ComputedModel(lambda: len(lst.value))
        self.assertEqual(length.value, 1)
        lst.value = [1, 2, 3]
        self.assertEqual(length.value, 3)


if __name__ == "__main__":
    unittest.main()
