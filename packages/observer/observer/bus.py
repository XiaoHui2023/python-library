from __future__ import annotations

from collections.abc import Callable
from threading import RLock
from typing import Any

from .context import ObserverContext


ObserverCallback = Callable[[ObserverContext], None]


class ObserverBus:
    def __init__(self) -> None:
        self._callbacks: list[tuple[ObserverCallback, dict[str, Any]]] = []
        self._lock = RLock()

    def subscribe(
        self,
        callback: ObserverCallback,
        **filters: Any,
    ) -> ObserverCallback:
        with self._lock:
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
            callbacks = tuple(self._callbacks)

        for callback, filters in callbacks:
            if not self._match_filters(ctx, filters):
                continue

            try:
                callback(ctx)
            except Exception:
                # 不要让监听器异常影响原始业务调用
                pass

    def observe(
        self,
        *,
        include_private: bool = False,
        emit_before: bool = True,
    ):
        from .deractor import observe_methods

        return observe_methods(
            self,
            include_private=include_private,
            emit_before=emit_before,
        )

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