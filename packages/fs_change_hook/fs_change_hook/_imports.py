"""集中导入 ``watchdog``，缺失时给出明确提示。"""

from __future__ import annotations

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "FSChangeHook 需要安装 watchdog：pip install watchdog"
    ) from exc

__all__ = ["FileSystemEvent", "FileSystemEventHandler", "Observer"]
