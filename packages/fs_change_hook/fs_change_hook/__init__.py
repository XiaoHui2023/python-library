"""监视文件系统路径变更（依赖 ``watchdog``）。"""

from __future__ import annotations

from .hook import FSChangeHook
from .once import FSChangeOnce, OnceWatchEnd
from .paths import expand_watch_paths, watch_paths_exist

__all__ = [
    "FSChangeHook",
    "FSChangeOnce",
    "OnceWatchEnd",
    "expand_watch_paths",
    "watch_paths_exist",
]
