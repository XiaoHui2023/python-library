from __future__ import annotations

import asyncio
import concurrent.futures
import inspect
import logging
from collections.abc import Awaitable, Callable
from threading import Event, RLock, Thread
from typing import Any, TypeVar

from .context import ObserverContext


_ClassT = TypeVar("_ClassT", bound=type[Any])

logger = logging.getLogger(__name__)

ObserverSyncCallback = Callable[[ObserverContext], None]
ObserverAsyncCallback = Callable[[ObserverContext], Awaitable[None]]
ObserverCallback = Callable[[ObserverContext], object]


class ObserverBus:
    def __init__(self, *, max_workers: int | None = None) -> None:
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
        with self._lock:
            self._callbacks = [
                (registered_callback, registered_filters)
                for registered_callback, registered_filters in self._callbacks
                if registered_callback is not callback
            ]

    def callback(self, **filters: Any):
        self._validate_filters(filters)

        def decorator(fn: ObserverCallback) -> ObserverCallback:
            return self.subscribe(fn, **filters)

        return decorator

    def emit(self, ctx: ObserverContext) -> None:
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
    ) -> Callable[[_ClassT], _ClassT]:
        from .deractor import observe_methods

        return observe_methods(
            self,
            include_private=include_private,
            emit_before=emit_before,
        )

    def close(self, *, wait: bool = True, timeout: float | None = None) -> None:
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
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
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