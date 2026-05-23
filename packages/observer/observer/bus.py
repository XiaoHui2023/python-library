from __future__ import annotations

import asyncio
import concurrent.futures
import inspect
import logging
from collections.abc import Awaitable, Callable
from threading import Event, RLock, Thread
from typing import Any, TypeVar

from .context import ObserverContext


T = TypeVar("T")

logger = logging.getLogger(__name__)

ObserverSyncCallback = Callable[[ObserverContext], None]
ObserverAsyncCallback = Callable[[ObserverContext], Awaitable[None]]
ObserverCallback = Callable[[ObserverContext], object]


class ObserverBus:
    """承载订阅、派发与收尾观测总线。

    在独立线程池中执行同步回调，在自建事件循环线程上调度协程回调；与业务线程解耦。
    """

    def __init__(self, *, max_workers: int | None = None) -> None:
        """创建总线并启动后台执行设施。

        Args:
            max_workers: 同步回调所用线程池的最大工作线程数；未指定时由标准库采用默认策略。
        """
        self._callbacks: list[tuple[ObserverCallback, dict[str, Any]]] = []
        self._pending: set[concurrent.futures.Future[Any]] = set()
        self._lock = RLock()
        self._closed = False

        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="observer-callback",
        )

        self._loop = asyncio.new_event_loop()
        self._loop_ready = Event()
        self._loop_thread = Thread(
            target=self._run_event_loop,
            name="observer-async-loop",
            daemon=True,
        )
        self._loop_thread.start()
        self._loop_ready.wait()

    def subscribe(
        self,
        callback: ObserverCallback,
        **filters: Any,
    ) -> ObserverCallback:
        """注册监听，在派发上下文与附带条件一致时触发。

        Args:
            callback: 同步函数、协程函数，或协程可调用实例；入参为当前派发快照。
            **filters: 与快照各槽位逐项相等的匹配条件；留空表示每次派发都考虑该回调。

        Returns:
            传入的监听对象，便于链式注册或稍后取消订阅。

        Raises:
            RuntimeError: 总线已关闭后仍尝试注册。
            ValueError: 匹配条件里出现了快照中不存在的字段名。
        """
        self._validate_filters(filters)

        with self._lock:
            if self._closed:
                raise RuntimeError("observer bus is closed")

            exists = any(
                registered_callback is callback and registered_filters == filters
                for registered_callback, registered_filters in self._callbacks
            )
            if not exists:
                self._callbacks.append((callback, dict(filters)))
        return callback

    def unsubscribe(self, callback: ObserverCallback) -> None:
        """按对象身份移除此前注册过的监听，与注册时使用的过滤条件无关。

        Args:
            callback: 与订阅时传入的同一可调用对象。
        """
        with self._lock:
            self._callbacks = [
                (registered_callback, registered_filters)
                for registered_callback, registered_filters in self._callbacks
                if registered_callback is not callback
            ]

    def callback(self, **filters: Any):
        """返回用于声明式注册监听的装饰器工厂。

        Args:
            **filters: 与订阅接口相同的匹配条件；非法字段名在装饰器应用时即校验。

        Returns:
            接收可调用对象并完成注册的装饰器。

        Raises:
            ValueError: 匹配条件里出现了快照中不存在的字段名。
        """
        self._validate_filters(filters)

        def decorator(fn: ObserverCallback) -> ObserverCallback:
            return self.subscribe(fn, **filters)

        return decorator

    def emit(self, ctx: ObserverContext) -> None:
        """向当前所有监听异步投递一份上下文快照；总线已关闭时静默忽略。

        Args:
            ctx: 本次派发携带的快照，监听侧按匹配条件决定是否执行。
        """
        with self._lock:
            if self._closed:
                return
            callbacks = tuple(self._callbacks)

        for callback, filters in callbacks:
            if not self._match_filters(ctx, filters):
                continue
            self._submit_callback(callback, ctx)

    def observe(
        self,
        *,
        include_private: bool = False,
        emit_before: bool = True,
    ) -> Callable[[type[T]], type[T]]:
        """返回类装饰器，为被装饰类的方法挂上与当前总线关联的观测包装。

        Args:
            include_private: 为真时下划线开头的方法也会被包装。
            emit_before: 为真时在目标方法体执行前额外派发切入阶段快照。

        Returns:
            接收类型对象并原地改写其可调用成员的类装饰器。
        """
        from .deractor import observe_methods

        return observe_methods(
            self,
            include_private=include_private,
            emit_before=emit_before,
        )

    def close(self, *, wait: bool = True, timeout: float | None = None) -> None:
        """停止接受新订阅并尽量结束在途回调。

        Args:
            wait: 为真时先等待已提交任务结束再关停执行设施。
            timeout: 等待在途同步任务或后台线程结束的上限秒数；与标准库等待语义一致。
        """
        with self._lock:
            if self._closed:
                return
            self._closed = True
            pending = tuple(self._pending)

        if wait and pending:
            concurrent.futures.wait(pending, timeout=timeout)

        self._executor.shutdown(wait=wait, cancel_futures=not wait)

        if not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._loop.stop)

        join_timeout = timeout if timeout is not None else (None if wait else 0.0)
        self._loop_thread.join(join_timeout)

    def __enter__(self) -> ObserverBus:
        """进入上下文管理作用域时返回自身。"""
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """离开上下文管理作用域时按同步等待策略关闭总线。

        Args:
            exc_type: 离开作用域时未处理异常的型别；无异常时为 None。
            exc: 异常实例或 None。
            tb: 对应回溯或 None。
        """
        self.close(wait=True)

    def _submit_callback(self, callback: ObserverCallback, ctx: ObserverContext) -> None:
        if self._is_async_callback(callback):
            future = asyncio.run_coroutine_threadsafe(
                self._run_async_callback(callback, ctx),
                self._loop,
            )
        else:
            future = self._executor.submit(callback, ctx)

        self._track_future(callback, future)

    def _track_future(
        self,
        callback: ObserverCallback,
        future: concurrent.futures.Future[Any],
    ) -> None:
        with self._lock:
            if self._closed:
                future.cancel()
                return
            self._pending.add(future)

        future.add_done_callback(
            lambda done_future: self._on_future_done(callback, done_future)
        )

    def _on_future_done(
        self,
        callback: ObserverCallback,
        future: concurrent.futures.Future[Any],
    ) -> None:
        with self._lock:
            self._pending.discard(future)

        try:
            future.result()
        except concurrent.futures.CancelledError:
            return
        except Exception:
            logger.exception(
                "observer callback failed: %s",
                self._callback_name(callback),
            )

    def _run_event_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop_ready.set()

        try:
            self._loop.run_forever()
        finally:
            pending = asyncio.all_tasks(self._loop)
            for task in pending:
                task.cancel()

            if pending:
                self._loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )

            self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            self._loop.close()

    async def _run_async_callback(
        self,
        callback: ObserverCallback,
        ctx: ObserverContext,
    ) -> None:
        result = callback(ctx)
        if inspect.isawaitable(result):
            await result

    def _is_async_callback(self, callback: ObserverCallback) -> bool:
        if inspect.iscoroutinefunction(callback):
            return True

        call = getattr(callback, "__call__", None)
        if call is not None and inspect.iscoroutinefunction(call):
            return True

        return False

    def _callback_name(self, callback: ObserverCallback) -> str:
        return getattr(callback, "__qualname__", getattr(callback, "__name__", repr(callback)))

    def _match_filters(self, ctx: ObserverContext, filters: dict[str, Any]) -> bool:
        for key, expected in filters.items():
            if getattr(ctx, key) != expected:
                return False
        return True

    def _validate_filters(self, filters: dict[str, Any]) -> None:
        valid_keys = set(ObserverContext.__dataclass_fields__.keys())
        invalid_keys = [key for key in filters if key not in valid_keys]
        if invalid_keys:
            raise ValueError(
                f"invalid callback filters: {', '.join(sorted(invalid_keys))}"
            )