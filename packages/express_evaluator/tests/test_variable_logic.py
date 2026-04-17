from __future__ import annotations

import unittest

from express_evaluator.variable_logic import (
    is_single_placeholder,
    replace_placeholders,
    resolve_path,
)
from express_evaluator.errors import UndefinedVariableError


class TestIsSinglePlaceholder(unittest.TestCase):
    def test_single_braced_var_returns_name(self) -> None:
        self.assertEqual(is_single_placeholder("{a}"), "a")
        self.assertEqual(is_single_placeholder("  {x.y}  "), "x.y")

    def test_not_single_returns_none(self) -> None:
        self.assertIsNone(is_single_placeholder("{a}{b}"))
        self.assertIsNone(is_single_placeholder("a"))
        self.assertIsNone(is_single_placeholder(""))


class TestResolvePath(unittest.TestCase):
    def test_mapping_chain(self) -> None:
        data = {"a": {"b": 1}}
        self.assertEqual(resolve_path(data, "a.b"), 1)

    def test_list_index(self) -> None:
        data = {"items": [10, 20]}
        self.assertEqual(resolve_path(data, "items.0"), 10)

    def test_strict_missing_key(self) -> None:
        with self.assertRaises(UndefinedVariableError):
            resolve_path({}, "a", strict=True)

    def test_non_strict_missing_returns_none(self) -> None:
        self.assertIsNone(resolve_path({}, "a", strict=False))

    def test_empty_segment_invalid(self) -> None:
        with self.assertRaises(UndefinedVariableError):
            resolve_path({"a": 1}, "a..b")

    def test_object_attribute(self) -> None:
        class Box:
            value = 42

        self.assertEqual(resolve_path(Box(), "value"), 42)

    def test_private_attribute_forbidden(self) -> None:
        class Box:
            _hidden = 1

        with self.assertRaises(UndefinedVariableError):
            resolve_path(Box(), "_hidden")


class TestReplacePlaceholders(unittest.TestCase):
    def test_replaces_with_internal_names(self) -> None:
        source, values = replace_placeholders("{a}", {"a": 1})
        self.assertTrue(source.startswith("__value_"))
        self.assertEqual(len(values), 1)
        self.assertEqual(list(values.values()), [1])

    def test_multiple_placeholders(self) -> None:
        source, values = replace_placeholders("{a} + {b}", {"a": 1, "b": 2})
        self.assertIn("__value_0", source)
        self.assertIn("__value_1", source)
        self.assertEqual(len(values), 2)


if __name__ == "__main__":
    unittest.main()
