from __future__ import annotations

import unittest

from ai_agent.harness.current_time import get_current_time


class TestHarnessCurrentTimeHelper(unittest.TestCase):
    def test_local_iso(self) -> None:
        text = get_current_time()
        self.assertRegex(text, r"^\d{4}-\d{2}-\d{2}T")

    def test_timezone_utc(self) -> None:
        text = get_current_time("UTC")
        self.assertTrue(text.endswith("+00:00") or text.endswith("Z"))

    def test_invalid_timezone(self) -> None:
        with self.assertRaises(ValueError):
            get_current_time("Not/A/Zone")


if __name__ == "__main__":
    unittest.main()
