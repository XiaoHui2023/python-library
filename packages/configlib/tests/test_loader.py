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


if __name__ == "__main__":
    unittest.main()
