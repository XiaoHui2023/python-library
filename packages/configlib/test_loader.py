from __future__ import annotations

import tempfile
import time
from pathlib import Path

from configlib import ConfigLoader


class AppConfig(ConfigLoader):
    name: str = ""
    port: int = 0
    debug: bool = False


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_loader() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        config_path = root / "config.json5"

        write_text(
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

        # 初次加载
        assert cfg.name == "demo"
        assert cfg.port == 8080
        assert cfg.debug is False

        # 文件没变化，不应重载
        assert cfg.reload() is False
        assert called == []

        # 修改文件后，应重载并触发回调
        time.sleep(0.01)
        write_text(
            config_path,
            """{
  name: "demo2",
  port: 9090,
  debug: true,
}""",
        )

        assert cfg.reload() is True
        assert cfg.name == "demo2"
        assert cfg.port == 9090
        assert cfg.debug is True
        assert called == [("demo2", 9090, True)]

        print("ConfigLoader 测试通过")


if __name__ == "__main__":
    test_loader()