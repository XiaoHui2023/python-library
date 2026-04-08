from __future__ import annotations
import sys
import inspect
import logging
import threading
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar

from configlib import load_config

from .changelog import ChangeLog
from .diff import build_object, diff_values
from .renderer import ChangeRenderer, DefaultRenderer

if sys.platform == "win32":
    import os
    os.system("")

logger = logging.getLogger(__name__)

T = TypeVar("T")
F = TypeVar("F", bound=Callable)


class WatchConfig(Generic[T]):
    """
    配置热更新器。

    实例化后作为装饰器注册回调函数，
    初次加载和每次文件变更时，回调收到一个完整的新配置对象。

    用法::

        watcher = WatchConfig("config.yaml", AppConfig)

        @watcher
        def on_config(cfg: AppConfig):
            ...

        watcher.start()
    """

    def __init__(
        self,
        file_path: str | Path,
        model_type: type[T],
        renderer: ChangeRenderer | None = None,
        *,
        interval: float = 1.0,
        debounce: float = 0.3,
        logger_: logging.Logger | None = None,
    ) -> None:
        self._file_path = Path(file_path).resolve()
        self._model_type = model_type
        self._renderer = renderer or DefaultRenderer()
        self._interval = interval
        self._debounce = debounce
        self._logger = logger_ or logger

        self._callbacks: list[Callable] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._file_state: tuple[int, int] | None = None
        self._raw_data: Any = None
        self._value: T | None = None

    def __call__(self, fn: F) -> F:
        """注册回调函数。支持作为装饰器使用。

        回调签名可以是：
            fn()
            fn(cfg)
            fn(cfg, changelog)
        """
        self._callbacks.append(fn)
        return fn

    @property
    def value(self) -> T | None:
        """当前配置对象。start() 之前为 None。"""
        return self._value

    @property
    def file_path(self) -> Path:
        return self._file_path

    def start(self) -> "WatchConfig[T]":
        """加载配置 → 调用回调 → 启动文件监控线程。"""
        if self._thread and self._thread.is_alive():
            return self

        self._load_and_notify()

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._watch_loop,
            name=f"WatchConfig:{self._file_path.name}",
            daemon=True,
        )
        self._thread.start()

        self._logger.info("WatchConfig started: %s", self._file_path)
        return self

    def stop(self) -> None:
        """停止文件监控。"""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._logger.info("WatchConfig stopped: %s", self._file_path)

    def run(self) -> None:
        """start + wait + stop 的快捷方式。Ctrl+C 可退出。"""
        self.start()
        try:
            self.wait()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def wait(self) -> None:
        """阻塞当前线程，直到 stop() 被调用。支持 Ctrl+C 中断。"""
        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=0.1)

    def reload(self) -> ChangeLog:
        """手动触发一次重新加载。"""
        return self._load_and_notify()

    def set_path(self, file_path: str | Path) -> "WatchConfig[T]":
        """修改配置文件路径并立即重新加载。"""
        self._file_path = Path(file_path).resolve()
        self._load_and_notify()
        return self

    def has_changed(self) -> bool:
        """检查配置文件是否发生了变化。"""
        try:
            state = self._get_file_state()
        except FileNotFoundError:
            return False
        return self._file_state is None or state != self._file_state

    def _load_and_notify(self) -> ChangeLog:
        new_data = self._read_config()
        new_obj = build_object(self._model_type, new_data)
        file_state = self._get_file_state()

        with self._lock:
            old_data = self._raw_data
            self._raw_data = new_data
            self._value = new_obj
            self._file_state = file_state

        if old_data is not None:
            changelog = diff_values(old_data, new_data)
        else:
            changelog = ChangeLog()


        if not changelog.is_empty:
            try:
                self._renderer.emit(changelog, self._logger)
            except Exception:
                self._logger.exception("Renderer failed")

        for cb in self._callbacks:
            try:
                _call_flexible(cb, new_obj, changelog)
            except Exception:
                self._logger.exception("Callback %r failed", cb)

        return changelog

    def _watch_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                if self.has_changed():
                    if self._stop_event.wait(self._debounce):
                        return

                    if self.has_changed():
                        try:
                            self._load_and_notify()
                        except Exception:
                            self._logger.exception(
                                "Config reload failed: %s",
                                self._file_path,
                            )
            except Exception:
                self._logger.exception("Watch loop error: %s", self._file_path)

            if self._stop_event.wait(self._interval):
                return

    def _read_config(self) -> Any:
        return load_config(str(self._file_path))

    def _get_file_state(self) -> tuple[int, int]:
        stat = self._file_path.stat()
        return (stat.st_mtime_ns, stat.st_size)


def _call_flexible(fn: Callable, obj: Any, changelog: ChangeLog) -> Any:
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return fn(obj, changelog)

    params = [
        p
        for p in sig.parameters.values()
        if p.default is inspect.Parameter.empty
        and p.kind
        not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )
    ]

    count = len(params)
    if count >= 2:
        return fn(obj, changelog)
    elif count == 1:
        return fn(obj)
    else:
        return fn()