"""在独立后台事件循环上调度异步回调（避免阻塞 watchdog 线程）。"""

from __future__ import annotations

import asyncio
import threading
from typing import Any


class _AsyncCallbackRunner:
    """按需启动守护线程 + ``asyncio`` 循环，用于 ``run_coroutine_threadsafe``。"""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()

    def _ensure(self) -> None:
        if self._thread is not None:
            return

        def run_loop() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            self._ready.set()
            loop.run_forever()

        t = threading.Thread(
            target=run_loop,
            name="fs-change-hook-async",
            daemon=True,
        )
        self._thread = t
        t.start()
        self._ready.wait()

    def schedule(self, coro: Any) -> None:
        self._ensure()
        assert self._loop is not None
        asyncio.run_coroutine_threadsafe(coro, self._loop)

    def close(self) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._loop = None
        self._thread = None
