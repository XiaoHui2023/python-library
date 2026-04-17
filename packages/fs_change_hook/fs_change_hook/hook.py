"""对外唯一入口：在若干路径上注册文件系统变更并触发回调。"""

from __future__ import annotations

import inspect
import threading
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Awaitable

from ._imports import Observer
from .async_runner import _AsyncCallbackRunner
from .event_handler import _FSChangeEventHandler
from .paths import expand_watch_paths

Callback = Callable[[], Any] | Callable[[], Awaitable[Any]]


class FSChangeHook:
    """
    使用 ``watchdog`` 监视若干文件或目录；在相关路径发生创建、修改、删除、移动等事件时调用回调。

    - 文件：监视其所在目录中的该文件（不递归子目录，除非该路径同时作为目录被监视）。
    - 目录：递归监视其下所有路径。
    - ``paths`` 可为字面路径，或含 ``* ? [`` 的 glob；glob 仅在 **无任何匹配串** 时报错。

    回调可在构造时传入，也可用实例作装饰器 ``@hook`` 注册；可注册多个。

    同步回调在 ``watchdog`` 观察者线程中执行；异步回调在独立后台事件循环中调度。
    请自行保证线程安全。

    ``debounce_seconds > 0`` 时启用防抖：路径上连续触发事件会重置计时，仅在最后一次变更后
    经过 ``debounce_seconds`` 仍无新事件时才调用回调（合并为一次）。
    """

    def __init__(
        self,
        paths: Sequence[str | Path],
        *callbacks: Callback,
        debounce_seconds: float = 0.0,
    ) -> None:
        if debounce_seconds < 0:
            raise ValueError("debounce_seconds must be >= 0")
        self._debounce_seconds = debounce_seconds
        self._debounce_timer: threading.Timer | None = None

        self._roots: list[Path] = expand_watch_paths(paths)
        self._callbacks: list[Callback] = list(callbacks)
        self._lock = threading.RLock()
        self._observer: Observer | None = None
        self._running = False
        self._async_runner: _AsyncCallbackRunner | None = None

        self._watched_files: set[Path] = {r for r in self._roots if r.is_file()}
        self._watched_dirs: set[Path] = {r for r in self._roots if r.is_dir()}

    def register(self, callback: Callback) -> None:
        """注册一个回调（与构造传入的回调一起被调用）。"""
        with self._lock:
            self._callbacks.append(callback)

    def unregister(self, callback: Callback) -> None:
        """移除已注册的回调。"""
        with self._lock:
            self._callbacks.remove(callback)

    def __call__(self, fn: Callback) -> Callback:
        """将函数注册为回调并返回原函数，便于 ``@hook`` 用法。"""
        self.register(fn)
        return fn

    def _path_triggers(self, path_str: str) -> bool:
        try:
            p = Path(path_str).resolve()
        except OSError:
            return False
        if p in self._watched_files:
            return True
        for d in self._watched_dirs:
            if p == d or p.is_relative_to(d):
                return True
        return False

    def _ensure_async_runner(self) -> _AsyncCallbackRunner:
        if self._async_runner is None:
            self._async_runner = _AsyncCallbackRunner()
        return self._async_runner

    def _on_watch_event(self) -> None:
        """由事件处理器在匹配到监视路径后调用。"""
        if self._debounce_seconds <= 0:
            self._invoke_callbacks()
            return
        self._schedule_debounced_invoke()

    def _schedule_debounced_invoke(self) -> None:
        with self._lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
                self._debounce_timer = None

            def _fire() -> None:
                with self._lock:
                    self._debounce_timer = None
                self._invoke_callbacks()

            t = threading.Timer(self._debounce_seconds, _fire)
            t.daemon = True
            self._debounce_timer = t
            t.start()

    def _invoke_callbacks(self) -> None:
        with self._lock:
            to_run = list(self._callbacks)
        for cb in to_run:
            if inspect.iscoroutinefunction(cb):
                self._ensure_async_runner().schedule(cb())
            else:
                cb()

    def _dirs_to_schedule(self) -> list[Path]:
        """若已有祖先目录在监视列表中，则不再为子目录单独注册观察者。"""
        ordered = sorted(self._watched_dirs, key=lambda p: (len(p.parts), str(p)))
        out: list[Path] = []
        for d in ordered:
            if any(d.is_relative_to(p) for p in out):
                continue
            out.append(d)
        return out

    def _files_needing_own_schedule(self) -> list[Path]:
        """已被目录监视覆盖的文件不再单独 schedule 父目录。"""
        out: list[Path] = []
        for f in self._watched_files:
            if any(f == d or f.is_relative_to(d) for d in self._watched_dirs):
                continue
            out.append(f)
        return out

    def start(self) -> None:
        """
        启动 ``watchdog`` 观察者。观察者运行在库自己的后台线程中，**本方法会立即返回**，
        不会阻塞调用线程（与 ``Observer.start()`` 语义一致）。
        已启动时不会重复启动。
        """
        with self._lock:
            if self._running:
                return

            handler = _FSChangeEventHandler(self)
            observer = Observer()
            scheduled: set[tuple[str, bool]] = set()

            for d in self._dirs_to_schedule():
                key = (str(d), True)
                if key in scheduled:
                    continue
                observer.schedule(handler, str(d), recursive=True)
                scheduled.add(key)

            for f in self._files_needing_own_schedule():
                parent = f.parent
                key = (str(parent), False)
                if key in scheduled:
                    continue
                observer.schedule(handler, str(parent), recursive=False)
                scheduled.add(key)

            observer.start()
            self._observer = observer
            self._running = True

    def stop(self) -> None:
        """停止观察者并等待其线程结束。"""
        with self._lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
                self._debounce_timer = None
            obs = self._observer
            self._observer = None
            self._running = False
            ar = self._async_runner
            self._async_runner = None

        if obs is not None:
            obs.stop()
            obs.join(timeout=5)
        if ar is not None:
            ar.close()
