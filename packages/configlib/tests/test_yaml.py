from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from configlib import load_config, load_config_raw
from configlib.yaml import is_yaml, load_yaml_raw


class ConfiglibYamlTests(unittest.TestCase):
    def test_load_example_yaml(self) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        result = load_config(str(base_dir / "assets" / "example.yaml"))

        expected = {
            "app": {
                "name": "demo",
                "version": "1.0",
            },
            "base": {
                "title": "hello",
                "nested": {
                    "value": 123,
                },
            },
            "json_data": {
                "user": {
                    "name": "alice",
                    "age": 18,
                },
            },
            "toml_data": {
                "server": {
                    "host": "127.0.0.1",
                    "port": 8080,
                },
            },
            "refs": {
                "app_name": "demo",
                "base_title": "hello",
                "local": {
                    "name": "child",
                    "parent_name": "child",
                },
            },
        }

        self.assertEqual(result, expected)

    def test_is_yaml_suffixes(self) -> None:
        self.assertTrue(is_yaml("a.yaml"))
        self.assertTrue(is_yaml("b.yml"))
        self.assertFalse(is_yaml("c.json"))

    def test_load_yaml_raw_keeps_placeholders(self) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        path = base_dir / "assets" / "example.yaml"
        data = load_yaml_raw(str(path))
        self.assertEqual(data["refs"]["app_name"], "${app.name}")

    def test_load_config_raw_yaml_matches_load_yaml_raw(self) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        path = base_dir / "assets" / "example.yaml"
        self.assertEqual(load_config_raw(path), load_yaml_raw(str(path)))

    def test_include_cycle_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "a.yaml"
            b = root / "b.yaml"
            a.write_text("v: !include b.yaml\n", encoding="utf-8")
            b.write_text("v: !include a.yaml\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "循环 include"):
                load_config(str(a))


if __name__ == "__main__":
    unittest.main()
