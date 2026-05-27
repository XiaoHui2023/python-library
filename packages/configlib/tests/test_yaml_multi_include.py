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
