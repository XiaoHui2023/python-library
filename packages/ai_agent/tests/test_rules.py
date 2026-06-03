from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_agent.rule import RuleSet


class RuleSetTests(unittest.TestCase):
    def test_build_concatenates_files_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a.md"
            second = root / "b.md"
            first.write_text("规则 A", encoding="utf-8")
            second.write_text("规则 B", encoding="utf-8")
            rules = RuleSet([first, second])
            text = rules.build_system_prompt()
        self.assertEqual(text, "规则 A\n\n规则 B")

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(ValueError):
            RuleSet(["/nonexistent/rule.md"])


if __name__ == "__main__":
    unittest.main()
