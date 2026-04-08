from __future__ import annotations

import unittest
from dataclasses import dataclass

from pydantic import BaseModel

from watch_config import ChangeType
from watch_config.diff import build_object, diff_values


class DiffValuesTests(unittest.TestCase):
    def test_identical_primitives_empty(self) -> None:
        log = diff_values(1, 1)
        self.assertTrue(log.is_empty)

    def test_primitive_updated(self) -> None:
        log = diff_values(1, 2)
        self.assertEqual(len(log), 1)
        e = log.entries[0]
        self.assertEqual(e.type, ChangeType.UPDATED)
        self.assertEqual(e.path, "$")
        self.assertEqual(e.old_value, 1)
        self.assertEqual(e.new_value, 2)

    def test_type_changed(self) -> None:
        log = diff_values(1, "1")
        self.assertEqual(len(log), 1)
        self.assertEqual(log.entries[0].type, ChangeType.TYPE_CHANGED)

    def test_dict_key_added_removed_updated(self) -> None:
        old = {"a": 1, "b": 2}
        new = {"a": 10, "c": 3}
        log = diff_values(old, new)
        paths = {(e.type, e.path) for e in log.entries}
        self.assertIn((ChangeType.UPDATED, "$.a"), paths)
        self.assertIn((ChangeType.REMOVED, "$.b"), paths)
        self.assertIn((ChangeType.ADDED, "$.c"), paths)

    def test_list_length_change(self) -> None:
        log = diff_values([1, 2], [1])
        types_paths = [(e.type, e.path) for e in log.entries]
        self.assertIn((ChangeType.REMOVED, "$[1]"), types_paths)

    def test_list_item_updated(self) -> None:
        log = diff_values([1, 2], [1, 3])
        self.assertEqual(len(log), 1)
        self.assertEqual(log.entries[0].path, "$[1]")
        self.assertEqual(log.entries[0].type, ChangeType.UPDATED)

    def test_tuple_treated_as_sequence(self) -> None:
        log = diff_values((1,), (1, 2))
        added = [e for e in log.entries if e.type == ChangeType.ADDED]
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0].path, "$[1]")

    def test_set_unequal_single_updated(self) -> None:
        log = diff_values({1, 2}, {1, 3})
        self.assertEqual(len(log), 1)
        self.assertEqual(log.entries[0].type, ChangeType.UPDATED)

    def test_set_equal_empty(self) -> None:
        log = diff_values({1}, {1})
        self.assertTrue(log.is_empty)

    def test_nested_dict_non_identifier_key_in_path(self) -> None:
        old = {"a-b": 1}
        new = {"a-b": 2}
        log = diff_values(old, new)
        self.assertTrue(any("a-b" in e.path for e in log.entries))

    def test_reuses_out_parameter(self) -> None:
        from watch_config import ChangeLog

        out = ChangeLog()
        diff_values({"x": 1}, {"x": 2}, out=out)
        self.assertFalse(out.is_empty)


@dataclass
class SampleDC:
    name: str
    count: int


class SampleModel(BaseModel):
    name: str
    count: int = 0


class BuildObjectTests(unittest.TestCase):
    def test_dict_model_requires_dict_payload(self) -> None:
        self.assertEqual(build_object(dict, {"a": 1}), {"a": 1})
        with self.assertRaises(TypeError):
            build_object(dict, [])

    def test_list_model(self) -> None:
        self.assertEqual(build_object(list, [1, 2]), [1, 2])
        with self.assertRaises(TypeError):
            build_object(list, {})

    def test_set_model_from_list(self) -> None:
        self.assertEqual(build_object(set, [1, 2]), {1, 2})

    def test_set_model_from_set(self) -> None:
        self.assertEqual(build_object(set, {1}), {1})

    def test_set_model_invalid_payload(self) -> None:
        with self.assertRaises(TypeError):
            build_object(set, "nope")

    def test_dataclass_from_dict(self) -> None:
        obj = build_object(SampleDC, {"name": "x", "count": 3})
        self.assertIsInstance(obj, SampleDC)
        self.assertEqual(obj.name, "x")
        self.assertEqual(obj.count, 3)

    def test_dataclass_requires_dict(self) -> None:
        with self.assertRaises(TypeError):
            build_object(SampleDC, [])

    def test_pydantic_model_validate(self) -> None:
        obj = build_object(SampleModel, {"name": "p", "count": 5})
        self.assertIsInstance(obj, SampleModel)
        self.assertEqual(obj.name, "p")
        self.assertEqual(obj.count, 5)

    def test_plain_class_kwargs_from_dict(self) -> None:
        class Box:
            def __init__(self, w: int, h: int) -> None:
                self.w = w
                self.h = h

        obj = build_object(Box, {"w": 2, "h": 3})
        self.assertEqual(obj.w, 2)
        self.assertEqual(obj.h, 3)

    def test_plain_callable_payload(self) -> None:
        obj = build_object(int, "42")
        self.assertEqual(obj, 42)


if __name__ == "__main__":
    unittest.main()
