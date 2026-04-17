"""watchdog 事件处理：过滤路径后触发钩子回调。"""

from __future__ import annotations

from typing import Any

from ._imports import FileSystemEvent, FileSystemEventHandler


class _FSChangeEventHandler(FileSystemEventHandler):
    def __init__(self, hook: Any) -> None:
        self._hook = hook

    def on_any_event(self, event: FileSystemEvent) -> None:
        candidates: list[str] = [event.src_path]
        dest = getattr(event, "dest_path", None)
        if dest:
            candidates.append(dest)
        if not any(self._hook._path_triggers(p) for p in candidates):
            return
        self._hook._on_watch_event()
