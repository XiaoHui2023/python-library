from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from patch_bay.rulebook import load_rulebook_from_json_file, merge_rulebook


class TestRulebook(unittest.TestCase):
    def test_load_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "rules.json"
            p.write_text(
                json.dumps({"r1": "True", "r2": '{type} == "message"'}, ensure_ascii=False),
                encoding="utf-8",
            )
            d = load_rulebook_from_json_file(p)
            self.assertEqual(d["r1"], "True")
            self.assertIn("type", d["r2"])

    def test_merge(self) -> None:
        self.assertEqual(
            merge_rulebook({"a": "1"}, {"a": "2", "b": "3"}),
            {"a": "2", "b": "3"},
        )


if __name__ == "__main__":
    unittest.main()
