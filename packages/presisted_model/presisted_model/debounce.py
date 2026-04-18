from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable[[], None])


class DebouncedAction:
    """
    首次 `schedule` 启动固定 `delay` 计时；同一轮内后续 `schedule` 不重置计时器，
    计时结束时执行一次回调（应读取当前最新状态）。执行后进入下一轮，再次 `schedule` 才重新计时。

    与「每次 schedule 都重置」的防抖不同：持续触发也会在首轮 `delay` 后落盘，不会因抖动无限推迟。
    """

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
                return
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
