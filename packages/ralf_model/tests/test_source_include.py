from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ralf_model import RalfSourceError, load_ralf_file
from ralf_model.source_expand import expand_ralf_sources, resolve_source_path


class SourceIncludeTests(unittest.TestCase):
    def test_resolve_relative_then_include_dir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inc = root / "inc"
            inc.mkdir()
            (inc / "chip.inc").write_text(
                "block sub {\n  bytes 2;\n}\n",
                encoding="utf-8",
            )
            top = root / "top.ralf"
            top.write_text('source "chip.inc"\n', encoding="utf-8")

            # 不在 top 同目录：仅靠 include 找到
            with self.assertRaises(RalfSourceError):
                resolve_source_path(
                    "chip.inc",
                    base_dir=top.parent,
                    include_paths=(),
                )

            r = resolve_source_path(
                "chip.inc",
                base_dir=top.parent,
                include_paths=(inc,),
            )
            self.assertEqual(r.resolve(), (inc / "chip.inc").resolve())

            doc = load_ralf_file(top, include_paths=(inc,))
            self.assertEqual(doc.blocks[0].name, "sub")
            self.assertEqual(doc.blocks[0].bytes_width, 2)

    def test_expand_recursive_source(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "leaf.ralf").write_text(
                "block leaf {\n bytes 1;\n}\n",
                encoding="utf-8",
            )
            (root / "mid.ralf").write_text('source "leaf.ralf"\n', encoding="utf-8")
            top = root / "top.ralf"
            top.write_text('source "mid.ralf"\n', encoding="utf-8")

            out = expand_ralf_sources(
                top.read_text(encoding="utf-8"),
                current_file=top.resolve(),
                include_paths=(),
                encoding="utf-8",
            )
            self.assertIn("block leaf", out)
            doc = load_ralf_file(top)
            self.assertEqual(doc.blocks[0].name, "leaf")

    def test_source_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = root / "a.ralf"
            b = root / "b.ralf"
            a.write_text('source "b.ralf"\n', encoding="utf-8")
            b.write_text('source "a.ralf"\n', encoding="utf-8")

            with self.assertRaises(RalfSourceError) as ctx:
                expand_ralf_sources(
                    a.read_text(encoding="utf-8"),
                    current_file=a.resolve(),
                    include_paths=(),
                )
            self.assertIn("循环", str(ctx.exception))

    def test_loads_expand_source_false(self) -> None:
        from ralf_model import loads_ralf

        raw = "block z { bytes 1; }\n"
        doc = loads_ralf(raw, expand_source=False)
        self.assertEqual(doc.blocks[0].name, "z")


if __name__ == "__main__":
    unittest.main()
