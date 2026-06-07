from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_agent.harness import Harness


class TestHarnessSandbox(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._root = Path(self._tmp.name)
        sample = self._root / "sample.txt"
        sample.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
        (self._root / "sub").mkdir()
        (self._root / "sub" / "inner.txt").write_text("in", encoding="utf-8")
        self._harness = Harness(self._root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_read_file_with_offset(self) -> None:
        text = self._harness.read_file("sample.txt", offset=2, limit=1)
        self.assertIn("beta", text)

    def test_write_file(self) -> None:
        msg = self._harness.write_file("out.txt", content="hello\n")
        self.assertIn("out.txt", msg)
        self.assertEqual((self._root / "out.txt").read_text(encoding="utf-8"), "hello\n")

    def test_list_files(self) -> None:
        listing = self._harness.list_files()
        self.assertIn("sample.txt", listing)
        self.assertIn("sub/", listing)

    def test_path_escape_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self._harness.read_file("../outside.txt")

    def test_run_python(self) -> None:
        text = self._harness.run_python("print(2 + 2)")
        self.assertIn("4", text)
        self.assertIn("退出码: 0", text)

    def test_workspace_info_no_absolute_path(self) -> None:
        info = self._harness.workspace_info()
        self.assertNotIn(str(self._root), info)

    def test_build_tools_names(self) -> None:
        tools = self._harness.build_tools()
        names = {t.name for t in tools}
        self.assertIn("harness__read_file", names)
        self.assertIn("harness__list_files", names)
        self.assertNotIn("harness__current_time", names)
        self.assertEqual(len(names), 6)


if __name__ == "__main__":
    unittest.main()
