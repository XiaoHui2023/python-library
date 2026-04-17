from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable[[], None])


class DebouncedAction:
    """在 `delay` 秒内多次 `schedule`，只在静止满 `delay` 后执行最后一次预定的动作。"""

    __slots__ = ("_delay", "_fn", "_timer", "_lock", "_cancelled")

    def __init__(self, fn: F, delay: float) -> None:
        if delay < 0:
            raise ValueError("delay must be non-negative")
        self._fn = fn
        self._delay = delay
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._cancelled = False

    def schedule(self) -> None:
        if self._cancelled:
            return
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            timer = threading.Timer(self._delay, self._run)
            timer.daemon = True
            self._timer = timer
            timer.start()

    def _run(self) -> None:
        with self._lock:
            self._timer = None
        if not self._cancelled:
            self._fn()

    def flush(self) -> None:
        """取消等待并立即执行一次（若未取消）。"""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
        if not self._cancelled:
            self._fn()

    def cancel(self) -> None:
        """取消待执行任务，之后 `schedule` / `flush` 不再执行回调。"""
        self._cancelled = True
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
