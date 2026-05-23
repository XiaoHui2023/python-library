from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from textwrap import dedent

from configlib import load_config, load_config_raw
from configlib.yaml_compose import apply_composition, preprocess_yaml_compose
from configlib.resolver import resolve_variables


class PreprocessTests(unittest.TestCase):
    def test_list_spread_line_gets_dash_placeholder(self) -> None:
        source = dedent("""
            items:
              - a
              ${extra}
              - b
        """)
        out = preprocess_yaml_compose(source)
        self.assertIn("- __configlib_spread__: ${extra}", out)

    def test_dict_merge_lines_collapsed(self) -> None:
        source = dedent("""
            cfg:
              ${base}
              ${more}
              flag: true
        """)
        out = preprocess_yaml_compose(source)
        self.assertIn("__configlib_merges__:", out)
        self.assertIn("- ${base}", out)
        self.assertIn("- ${more}", out)


class ComposeIntegrationTests(unittest.TestCase):
    def test_list_spread_and_nested_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.yaml"
            path.write_text(
                dedent("""
                    shared: [s1, s2]
                    items:
                      - head
                      ${shared}
                      - tail
                """),
                encoding="utf-8",
            )
            data = load_config(path)
            self.assertEqual(data["items"], ["head", "s1", "s2", "tail"])

    def test_list_nested_variable_stays_one_element(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.yaml"
            path.write_text(
                dedent("""
                    shared: [1, 2]
                    items:
                      - ${shared}
                """),
                encoding="utf-8",
            )
            data = load_config(path)
            self.assertEqual(data["items"], [[1, 2]])

    def test_dict_deep_merge_nested_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.yaml"
            path.write_text(
                dedent("""
                    base:
                      x2:
                        x3: v1
                        x4: v2
                      x5: v3
                    x1:
                      ${base}
                      x2:
                        x4: vvvv
                """),
                encoding="utf-8",
            )
            data = load_config(path)
            self.assertEqual(
                data["x1"],
                {"x2": {"x3": "v1", "x4": "vvvv"}, "x5": "v3"},
            )

    def test_cfg_merge_base_then_nested_local_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.yaml"
            path.write_text(
                dedent("""
                    base:
                      a: 1
                      b:
                        c: old
                        d: keep
                    cfg:
                      ${base}
                      b:
                        c: v1
                """),
                encoding="utf-8",
            )
            data = load_config(path)
            self.assertEqual(
                data["cfg"],
                {"a": 1, "b": {"c": "v1", "d": "keep"}},
            )

    def test_include_then_deep_merge_via_variable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.yaml").write_text(
                dedent("""
                    x1:
                      x2:
                        x3: v1
                        x4: v2
                      x5: v3
                """),
                encoding="utf-8",
            )
            (root / "b.yaml").write_text(
                dedent("""
                    from_a: !include a.yaml
                    x1:
                      ${from_a.x1}
                      x2:
                        x4: vvvv
                """),
                encoding="utf-8",
            )
            data = load_config(root / "b.yaml")
            self.assertEqual(
                data["x1"],
                {"x2": {"x3": "v1", "x4": "vvvv"}, "x5": "v3"},
            )

    def test_dict_merge_then_local_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.yaml"
            path.write_text(
                dedent("""
                    base:
                      a: 1
                      b: old
                    cfg:
                      ${base}
                      b: new
                      c: 3
                """),
                encoding="utf-8",
            )
            data = load_config(path)
            self.assertEqual(data["cfg"], {"a": 1, "b": "new", "c": 3})

    def test_dict_nested_key_keeps_subtree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.yaml"
            path.write_text(
                dedent("""
                    base:
                      x: 1
                    root:
                      nested: ${base}
                """),
                encoding="utf-8",
            )
            data = load_config(path)
            self.assertEqual(data["root"]["nested"], {"x": 1})

    def test_raw_keeps_placeholders_without_resolve(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.yaml"
            path.write_text(
                dedent("""
                    items:
                      - head
                      ${shared}
                """),
                encoding="utf-8",
            )
            raw = load_config_raw(path)
            self.assertIn("__configlib_spread__", str(raw))

    def test_spread_non_list_raises(self) -> None:
        tree = resolve_variables({"n": 1, "items": [{"__configlib_spread__": "${n}"}]})
        with self.assertRaises(TypeError):
            apply_composition(tree)


class ComposeUnitTests(unittest.TestCase):
    def test_apply_list_spread(self) -> None:
        data = [{"__configlib_spread__": [1, 2]}, 3]
        self.assertEqual(apply_composition(data), [1, 2, 3])

    def test_apply_dict_merges(self) -> None:
        data = {
            "__configlib_merges__": [{"a": 1}, {"b": 2}],
            "b": 9,
        }
        self.assertEqual(apply_composition(data), {"a": 1, "b": 9})
