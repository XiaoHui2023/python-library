"""监视文件系统路径变更（依赖 ``watchdog``）。"""

from __future__ import annotations

from .hook import FSChangeHook

__all__ = ["FSChangeHook"]
