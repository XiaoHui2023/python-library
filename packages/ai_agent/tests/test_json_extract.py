from __future__ import annotations

import json
import unittest

from ai_agent.json_extract import extract_first_json_object, extract_first_json_value


class TestJsonExtract(unittest.TestCase):
    def test_trailing_text(self) -> None:
        payload = {"a": 1}
        raw = json.dumps(payload) + " 尾部说明"
        self.assertEqual(extract_first_json_object(raw), payload)

    def test_leading_prose(self) -> None:
        payload = {"steps": []}
        raw = "说明：" + json.dumps(payload)
        self.assertEqual(extract_first_json_object(raw), payload)

    def test_array_value(self) -> None:
        raw = '[1, 2] extra'
        self.assertEqual(extract_first_json_value(raw), [1, 2])
        self.assertIsNone(extract_first_json_object(raw))


if __name__ == "__main__":
    unittest.main()
