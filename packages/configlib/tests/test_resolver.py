from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from configlib.resolver import resolve_variables


class ResolverTests(unittest.TestCase):
    def test_pass_through_non_string_nodes(self) -> None:
        self.assertIsNone(resolve_variables(None))
        self.assertEqual(resolve_variables(42), 42)
        self.assertEqual(resolve_variables([1, {"a": 2}]), [1, {"a": 2}])

    def test_full_placeholder_resolves_sibling(self) -> None:
        data = {"a": 1, "b": "${a}"}
        self.assertEqual(resolve_variables(data)["b"], 1)

    def test_nested_path(self) -> None:
        data = {"x": {"y": "ok"}, "z": "${x.y}"}
        self.assertEqual(resolve_variables(data)["z"], "ok")

    def test_list_index_in_path(self) -> None:
        data = {"items": [{"id": 9}], "first": "${items.0.id}"}
        self.assertEqual(resolve_variables(data)["first"], 9)

    def test_relative_reference(self) -> None:
        data = {
            "block": {
                "name": "inner",
                "copy": "${..name}",
            },
            "name": "outer",
        }
        out = resolve_variables(data)
        self.assertEqual(out["block"]["copy"], "inner")

    def test_env_explicit(self) -> None:
        data = {"p": "${env:CFG_TEST_LIB_PORT}"}
        with patch.dict(os.environ, {"CFG_TEST_LIB_PORT": "3000"}, clear=False):
            self.assertEqual(resolve_variables(data)["p"], 3000)

    def test_env_with_default_when_missing(self) -> None:
        env_name = "CFG_TEST_LIB_SHOULD_NOT_EXIST_XYZ"
        self.assertIsNone(os.environ.get(env_name))
        data = {"p": "${env:" + env_name + ":fallback}"}
        self.assertEqual(resolve_variables(data)["p"], "fallback")

    def test_env_missing_raises(self) -> None:
        env_name = "CFG_TEST_LIB_ABSENT_VAR"
        self.assertIsNone(os.environ.get(env_name))
        data = {"p": "${env:" + env_name + "}"}
        with self.assertRaises(KeyError):
            resolve_variables(data)

    def test_single_segment_falls_back_to_env(self) -> None:
        name = "CFG_TEST_LIB_SINGLE"
        data = {"p": "${" + name + "}"}
        with patch.dict(os.environ, {name: "yes"}, clear=False):
            self.assertIs(resolve_variables(data)["p"], True)

    def test_partial_string_interpolation(self) -> None:
        data = {"host": "h", "s": "x-${host}-y"}
        self.assertEqual(resolve_variables(data)["s"], "x-h-y")

    def test_circular_reference_raises(self) -> None:
        data: dict[str, object] = {"a": "${b}", "b": "${a}"}
        with self.assertRaisesRegex(ValueError, "循环变量引用"):
            resolve_variables(data)

    def test_invalid_relative_path_raises(self) -> None:
        data = {"x": "${.bad}"}
        with self.assertRaisesRegex(ValueError, "不支持的相对路径变量"):
            resolve_variables(data)
