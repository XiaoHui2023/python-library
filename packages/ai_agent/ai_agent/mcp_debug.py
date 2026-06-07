from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import TextIO

_log_lock = Lock()


class McpDebugLog:
    """
    宿主侧 MCP 调试：生命周期事件写入文件，server stderr 经 ``server_stderr_sink`` 转发。

    路径来自构造参数或环境变量 ``AI_AGENT_MCP_DEBUG_LOG``。
    """

    def __init__(self, path: str | Path | None = None) -> None:
        if path is not None:
            resolved = Path(path).expanduser()
            self._path: Path | None = resolved if str(resolved).strip() else None
        else:
            raw = os.environ.get("AI_AGENT_MCP_DEBUG_LOG", "").strip()
            self._path = Path(raw).expanduser() if raw else None

    @property
    def enabled(self) -> bool:
        return self._path is not None

    def log(self, message: str) -> None:
        if self._path is None:
            return
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n"
        with _log_lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(line)

    def server_stderr_sink(self) -> TextIO:
        """供 ``stdio_client(..., errlog=...)`` 使用：终端 stderr + 可选文件。"""
        return _McpServerStderrTee(self)


class _McpServerStderrTee:
    def __init__(self, debug: McpDebugLog) -> None:
        self._debug = debug

    def write(self, data: str) -> int:
        if not data:
            return 0
        sys.stderr.write(data)
        sys.stderr.flush()
        if self._debug.enabled:
            for line in data.splitlines():
                stripped = line.strip()
                if stripped:
                    self._debug.log(f"[server stderr] {stripped}")
        return len(data)

    def flush(self) -> None:
        sys.stderr.flush()
