from __future__ import annotations

import unittest
from pathlib import Path

from configlib import load_config


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


if __name__ == "__main__":
    unittest.main()
