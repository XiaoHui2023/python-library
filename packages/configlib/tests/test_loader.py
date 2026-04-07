from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from configlib import ConfigLoader


class AppConfig(ConfigLoader):
    name: str = ""
    port: int = 0
    debug: bool = False


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


class ConfiglibLoaderTests(unittest.TestCase):
    def test_reload_and_on_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "config.json5"

            _write_text(
                config_path,
                """{
  name: "demo",
  port: 8080,
  debug: false,
}""",
            )

            called: list[tuple[str, int, bool]] = []

            def on_update(cfg: AppConfig) -> None:
                called.append((cfg.name, cfg.port, cfg.debug))

            cfg = AppConfig.from_file(
                file_path=str(config_path),
                on_update=on_update,
            )

            self.assertEqual(cfg.name, "demo")
            self.assertEqual(cfg.port, 8080)
            self.assertIs(cfg.debug, False)

            self.assertIs(cfg.reload(), False)
            self.assertEqual(called, [])

            time.sleep(0.01)
            _write_text(
                config_path,
                """{
  name: "demo2",
  port: 9090,
  debug: true,
}""",
            )

            self.assertIs(cfg.reload(), True)
            self.assertEqual(cfg.name, "demo2")
            self.assertEqual(cfg.port, 9090)
            self.assertIs(cfg.debug, True)
            self.assertEqual(called, [("demo2", 9090, True)])

    def test_from_file_missing_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nope.json5"
            with self.assertRaises(FileNotFoundError):
                AppConfig.from_file(missing)

    def test_from_file_rejects_non_dict_top_level(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "list.json5"
            _write_text(path, "[1, 2, 3]")
            with self.assertRaisesRegex(TypeError, "配置顶层必须是 dict"):
                AppConfig.from_file(path)

    def test_has_changed_detects_modification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "config.json5"
            _write_text(
                config_path,
                """{ name: "a", port: 1, debug: false }""",
            )
            cfg = AppConfig.from_file(config_path)
            self.assertFalse(cfg.has_changed())
            time.sleep(0.01)
            _write_text(
                config_path,
                """{ name: "b", port: 2, debug: true }""",
            )
            self.assertTrue(cfg.has_changed())

    def test_on_update_two_arg_receives_old_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "config.json5"
            _write_text(
                config_path,
                """{ name: "first", port: 1, debug: false }""",
            )
            events: list[tuple[str, str]] = []

            def on_update(new: AppConfig, old: AppConfig) -> None:
                events.append((new.name, old.name))

            cfg = AppConfig.from_file(config_path, on_update=on_update)
            time.sleep(0.01)
            _write_text(
                config_path,
                """{ name: "second", port: 1, debug: false }""",
            )
            self.assertTrue(cfg.reload())
            self.assertEqual(events, [("second", "first")])

    def test_on_update_zero_arg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "config.json5"
            _write_text(config_path, """{ name: "x", port: 1, debug: false }""")
            count = 0

            def on_update() -> None:
                nonlocal count
                count += 1

            cfg = AppConfig.from_file(config_path, on_update=on_update)
            time.sleep(0.01)
            _write_text(config_path, """{ name: "y", port: 1, debug: false }""")
            self.assertTrue(cfg.reload())
            self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
