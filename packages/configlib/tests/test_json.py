from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from configlib.json import is_json, load_json, load_json_raw


class JsonHelpersTests(unittest.TestCase):
    def test_is_json_suffixes(self) -> None:
        self.assertTrue(is_json("app.json"))
        self.assertTrue(is_json(r"C:\x\config.json5"))
        self.assertFalse(is_json("x.yaml"))
        self.assertFalse(is_json("noext"))

    def test_load_json_resolves_full_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json5"
            path.write_text(
                '{"port": 8080, "label": "${port}"}',
                encoding="utf-8",
            )
            data = load_json(str(path))
            self.assertEqual(data["label"], 8080)

    def test_load_json_raw_skips_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json5"
            path.write_text(
                '{"x": "${y}", "y": 1}',
                encoding="utf-8",
            )
            data = load_json_raw(str(path))
            self.assertEqual(data["x"], "${y}")

    def test_load_json_interpolates_in_string(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json5"
            path.write_text(
                '{"host": "127.0.0.1", "dsn": "postgres://${host}/db"}',
                encoding="utf-8",
            )
            data = load_json(str(path))
            self.assertEqual(data["dsn"], "postgres://127.0.0.1/db")
