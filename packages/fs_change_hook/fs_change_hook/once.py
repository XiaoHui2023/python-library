"""一次性阻塞等待路径上的下一次文件系统变更。"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Sequence
from enum import Enum
from pathlib import Path

from .hook import FSChangeHook


class OnceWatchEnd(str, Enum):
    """:meth:`FSChangeOnce.wait` / :meth:`FSChangeOnce.wait_async` 的结束原因。"""

    CHANGED = "changed"
    TIMEOUT = "timeout"


class FSChangeOnce:
    """
    只等待**一次**匹配 ``paths`` 的变更：在首次触发或超时后结束，并停止观察者、释放相关资源。

    同步使用 :meth:`wait`；在协程中使用 :meth:`wait_async`（内部用线程执行 ``wait``，不阻塞事件循环）。

    ``root``：与 :class:`FSChangeHook` 相同，用于解析相对路径。
    """

    def __init__(
        self,
        paths: Sequence[str | Path],
        *,
        debounce_seconds: float = 0.0,
        root: str | Path | None = None,
    ) -> None:
        self._paths = paths
        self._debounce_seconds = debounce_seconds
        self._root = root
        self._hook: FSChangeHook | None = None
        self._done = threading.Event()
        self._end: OnceWatchEnd | None = None
        self._last_end: OnceWatchEnd | None = None
        self._cb_lock = threading.Lock()

    @property
    def last_end(self) -> OnceWatchEnd | None:
        """最近一次 :meth:`wait` / :meth:`wait_async` 结束后的原因；尚未调用过时为 ``None``。"""
        return self._last_end

    def _on_change(self) -> None:
        with self._cb_lock:
            if self._end is not None:
                return
            self._end = OnceWatchEnd.CHANGED
        self._done.set()

    def wait(self, timeout: float | None = None) -> OnceWatchEnd:
        """
        阻塞直到首次匹配变更，或超过 ``timeout`` 秒（``None`` 表示无限等待）。

        返回结束原因；结束后 :attr:`last_end` 与返回值一致。
        """
        with self._cb_lock:
            self._end = None
        self._done.clear()

        hook = FSChangeHook(
            self._paths,
            self._on_change,
            debounce_seconds=self._debounce_seconds,
            root=self._root,
        )
        self._hook = hook
        hook.start()
        signalled = False
        try:
            signalled = self._done.wait(timeout)
            if not signalled:
                hook.stop()
                with self._cb_lock:
                    if self._end is None:
                        self._end = OnceWatchEnd.TIMEOUT
        finally:
            hook.stop()
            self._hook = None

        if self._end is not None:
            out = self._end
        elif signalled:
            out = OnceWatchEnd.CHANGED
        else:
            out = OnceWatchEnd.TIMEOUT
        self._last_end = out
        return out

    async def wait_async(self, timeout: float | None = None) -> OnceWatchEnd:
        """异步等待；内部 ``asyncio.to_thread(self.wait, …)``，不阻塞事件循环。"""
        return await asyncio.to_thread(self.wait, timeout)
