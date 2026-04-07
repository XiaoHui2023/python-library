from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from configlib import load_config, load_config_raw


class LoadConfigDispatchTests(unittest.TestCase):
    def test_unsupported_extension_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.txt"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "不支持的文件格式"):
                load_config(path)
            with self.assertRaisesRegex(ValueError, "不支持的文件格式"):
                load_config_raw(path)

    def test_load_config_accepts_path_object(self) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        path = base_dir / "assets" / "example.yaml"
        self.assertIsInstance(load_config(path), dict)

    def test_raw_does_not_resolve_variables(self) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        path = base_dir / "assets" / "example.yaml"
        data = load_config_raw(path)
        self.assertEqual(data["refs"]["app_name"], "${app.name}")

    def test_resolved_matches_full_tree(self) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        resolved = load_config(base_dir / "assets" / "example.yaml")
        raw = load_config_raw(base_dir / "assets" / "example.yaml")
        self.assertNotEqual(resolved["refs"]["app_name"], raw["refs"]["app_name"])
        self.assertEqual(resolved["refs"]["app_name"], "demo")
