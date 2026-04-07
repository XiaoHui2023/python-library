from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from configlib.toml import is_toml, load_toml, load_toml_raw


class TomlHelpersTests(unittest.TestCase):
    def test_is_toml_suffix(self) -> None:
        self.assertTrue(is_toml("cfg.toml"))
        self.assertFalse(is_toml("x.json"))

    def test_load_toml_resolves_variables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.toml"
            path.write_text(
                '[app]\nname = "demo"\nlabel = "${app.name}"\n',
                encoding="utf-8",
            )
            data = load_toml(str(path))
            self.assertEqual(data["app"]["label"], "demo")

    def test_load_toml_raw_no_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.toml"
            path.write_text(
                'x = "${y}"\ny = 1\n',
                encoding="utf-8",
            )
            data = load_toml_raw(str(path))
            self.assertEqual(data["x"], "${y}")
