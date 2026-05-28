from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from textwrap import dedent

from configlib import load_config
from configlib.yaml_compose import preprocess_yaml_includes


class YamlMultiIncludeTests(unittest.TestCase):
    def _write_user_layout(self, root: Path) -> None:
        (root / "b.json").write_text(
            json.dumps({"a": {"name": 6}, "b": {"name": 7}}),
            encoding="utf-8",
        )
        (root / "c.yaml").write_text(
            "a:\n  freq: 128\n",
            encoding="utf-8",
        )
        (root / "spec.yaml").write_text(
            dedent(
                """
                vars:
                  nodes:
                    !include b.json
                    !include c.yaml
                """
            ),
            encoding="utf-8",
        )
        (root / "a.yaml").write_text(
            dedent(
                """
                !include spec.yaml

                class_prefix: CLock_
                trees:
                  - name: orion
                  - nodes: ${vars.nodes}
                """
            ),
            encoding="utf-8",
        )

    def test_preprocess_collapses_bare_includes(self) -> None:
        source = dedent(
            """
            root:
              !include a.json
              !include b.yaml
              flag: true
            """
        )
        out = preprocess_yaml_includes(source)
        self.assertIn("__configlib_includes__:", out)
        self.assertIn("- a.json", out)
        self.assertIn("- b.yaml", out)

    def test_user_multi_file_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_user_layout(root)
            data = load_config(root / "a.yaml")
            self.assertEqual(data["class_prefix"], "CLock_")
            self.assertEqual(
                data["vars"]["nodes"],
                {"a": {"name": 6, "freq": 128}, "b": {"name": 7}},
            )
            self.assertEqual(
                data["trees"],
                [
                    {"name": "orion"},
                    {"nodes": {"a": {"name": 6, "freq": 128}, "b": {"name": 7}}},
                ],
            )

    def test_root_include_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "inner.yaml").write_text("x: 1\n", encoding="utf-8")
            (root / "main.yaml").write_text("!include inner.yaml\n", encoding="utf-8")
            self.assertEqual(load_config(root / "main.yaml"), {"x": 1})

    def test_preprocess_keyed_include_with_bare_sibling(self) -> None:
        source = dedent(
            """
            a: !include xx1.yaml
              !include xx2.yaml
            """
        )
        out = preprocess_yaml_includes(source)
        self.assertIn("a:\n", out)
        self.assertIn("__configlib_includes__:", out)
        self.assertIn("- xx1.yaml", out)
        self.assertIn("- xx2.yaml", out)
        self.assertNotIn("a: !include", out)

    def test_keyed_include_plus_bare_include_merges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "xx1.yaml").write_text("x: 1\n", encoding="utf-8")
            (root / "xx2.yaml").write_text("y: 2\n", encoding="utf-8")
            (root / "main.yaml").write_text(
                dedent(
                    """
                    a: !include xx1.yaml
                      !include xx2.yaml
                    """
                ),
                encoding="utf-8",
            )
            self.assertEqual(load_config(root / "main.yaml"), {"a": {"x": 1, "y": 2}})

    def test_keyed_include_plus_bare_and_local_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "base.yaml").write_text("a: 1\nb:\n  c: old\n", encoding="utf-8")
            (root / "extra.yaml").write_text("d: 4\n", encoding="utf-8")
            (root / "main.yaml").write_text(
                dedent(
                    """
                    cfg: !include base.yaml
                      !include extra.yaml
                      b:
                        c: new
                    """
                ),
                encoding="utf-8",
            )
            data = load_config(root / "main.yaml")
            self.assertEqual(
                data["cfg"],
                {"a": 1, "b": {"c": "new"}, "d": 4},
            )

    def test_preprocess_standalone_keyed_include(self) -> None:
        source = "a: !include xx.yaml\n"
        out = preprocess_yaml_includes(source)
        self.assertIn("a:\n", out)
        self.assertIn("__configlib_includes__:", out)
        self.assertIn("- xx.yaml", out)
        self.assertNotIn("a: !include", out)

    def test_keyed_and_block_include_equivalent_for_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data.yaml").write_text("x: 1\ny: 2\n", encoding="utf-8")
            keyed = dedent(
                """
                a: !include data.yaml
                """
            )
            block = dedent(
                """
                a:
                  !include data.yaml
                """
            )
            (root / "keyed.yaml").write_text(keyed, encoding="utf-8")
            (root / "block.yaml").write_text(block, encoding="utf-8")
            expected = {"x": 1, "y": 2}
            self.assertEqual(load_config(root / "keyed.yaml")["a"], expected)
            self.assertEqual(load_config(root / "block.yaml")["a"], expected)

    def test_keyed_and_block_include_equivalent_for_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "items.yaml").write_text("- 1\n- 2\n", encoding="utf-8")
            keyed = "a: !include items.yaml\n"
            block = dedent(
                """
                a:
                  !include items.yaml
                """
            )
            (root / "keyed.yaml").write_text(keyed, encoding="utf-8")
            (root / "block.yaml").write_text(block, encoding="utf-8")
            expected = [1, 2]
            self.assertEqual(load_config(root / "keyed.yaml")["a"], expected)
            self.assertEqual(load_config(root / "block.yaml")["a"], expected)

    def test_keyed_include_multiple_paths_on_one_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "1.yaml").write_text("a: 1\n", encoding="utf-8")
            (root / "2.yaml").write_text("b: 2\n", encoding="utf-8")
            (root / "3.json").write_text('{"c": 3}', encoding="utf-8")
            (root / "4.toml").write_text('d = 4\n', encoding="utf-8")
            (root / "main.yaml").write_text(
                "cfg: !include 1.yaml 2.yaml 3.json 4.toml\n",
                encoding="utf-8",
            )
            self.assertEqual(
                load_config(root / "main.yaml")["cfg"],
                {"a": 1, "b": 2, "c": 3, "d": 4},
            )

    def test_keyed_multi_path_equivalent_to_block_mixed_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "1.yml").write_text("x: 1\n", encoding="utf-8")
            (root / "2.yaml").write_text("y: 2\n", encoding="utf-8")
            (root / "3.json").write_text('{"z": 3}', encoding="utf-8")
            (root / "4.toml").write_text('w = 4\n', encoding="utf-8")
            one_line = "a: !include 1.yml 2.yaml 3.json 4.toml\n"
            block = dedent(
                """
                a:
                  !include 1.yml
                  !include 2.yaml 3.json
                  !include 4.toml
                """
            )
            (root / "one.yaml").write_text(one_line, encoding="utf-8")
            (root / "block.yaml").write_text(block, encoding="utf-8")
            expected = {"x": 1, "y": 2, "z": 3, "w": 4}
            self.assertEqual(load_config(root / "one.yaml")["a"], expected)
            self.assertEqual(load_config(root / "block.yaml")["a"], expected)

    def test_preprocess_keyed_multiple_paths(self) -> None:
        source = "a: !include one.yaml two.json\n"
        out = preprocess_yaml_includes(source)
        self.assertIn("- one.yaml", out)
        self.assertIn("- two.json", out)

    def test_multiple_list_includes_concatenate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.yaml").write_text("- 1\n", encoding="utf-8")
            (root / "b.yaml").write_text("- 2\n", encoding="utf-8")
            (root / "main.yaml").write_text(
                dedent(
                    """
                    items:
                      !include a.yaml
                      !include b.yaml
                    """
                ),
                encoding="utf-8",
            )
            self.assertEqual(load_config(root / "main.yaml")["items"], [1, 2])

    def test_bare_include_then_local_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "base.yaml").write_text(
                "a: 1\nb:\n  c: old\n",
                encoding="utf-8",
            )
            (root / "main.yaml").write_text(
                dedent(
                    """
                    cfg:
                      !include base.yaml
                      b:
                        c: new
                    """
                ),
                encoding="utf-8",
            )
            data = load_config(root / "main.yaml")
            self.assertEqual(data["cfg"], {"a": 1, "b": {"c": "new"}})


if __name__ == "__main__":
    unittest.main()
