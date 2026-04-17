"""expand_watch_paths 单元测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fs_change_hook.paths import expand_watch_paths


class TestExpandWatchPaths(unittest.TestCase):
    def test_empty_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            expand_watch_paths([])
        self.assertIn("at least one", str(ctx.exception).lower())

    def test_literal_missing_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            expand_watch_paths([Path("___nonexistent_fs_change_hook___")])

    def test_literal_file_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "a.txt"
            f.write_text("x", encoding="utf-8")
            roots = expand_watch_paths([f])
            self.assertEqual(len(roots), 1)
            self.assertEqual(roots[0].resolve(), f.resolve())

    def test_literal_dir_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            roots = expand_watch_paths([d])
            self.assertEqual(len(roots), 1)
            self.assertEqual(roots[0].resolve(), d.resolve())

    def test_glob_no_match_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            pattern = str(Path(td) / "no_such_*.txt")
            with self.assertRaises(FileNotFoundError) as ctx:
                expand_watch_paths([pattern])
            self.assertIn("no paths matched", str(ctx.exception).lower())

    def test_glob_finds_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "x1.txt").write_text("a", encoding="utf-8")
            (base / "x2.txt").write_text("b", encoding="utf-8")
            pattern = str(base / "x*.txt")
            roots = expand_watch_paths([pattern])
            names = {p.name for p in roots}
            self.assertEqual(names, {"x1.txt", "x2.txt"})

    def test_dedupes_same_target(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "a.txt"
            f.write_text("x", encoding="utf-8")
            roots = expand_watch_paths([f, f])
            self.assertEqual(len(roots), 1)


if __name__ == "__main__":
    unittest.main()
