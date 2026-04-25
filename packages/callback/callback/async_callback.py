from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, ClassVar, TypeVar

from callback.base import CallbackBase, T, _CallbackPydanticMeta


def _require_async_handler(func: Callable[..., Any]) -> None:
    if not inspect.iscoroutinefunction(func):
        raise TypeError(
            "继承 AsyncCallback 的子类只登记 async def；普通函数请使用继承 Callback 的子类。",
        )


class _AsyncCallbackMeta(_CallbackPydanticMeta):
    """对子类做类调用时：单参可调用须为协程函数，否则与异步 `trigger` 相同。"""

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if len(args) == 1 and not kwargs and callable(args[0]):
            func = args[0]
            cls.register(func)
            return func
        return cls.trigger(*args, **kwargs)


class AsyncCallback(CallbackBase, metaclass=_AsyncCallbackMeta):
    """异步根：在协程里 `await` 跑管线，处理函数仅能为协程；层内用 asyncio 并发。"""

    __callback_is_root__: ClassVar[bool] = True

    @classmethod
    def before(cls, func: Callable[..., Any]) -> Callable[..., Any]:
        _require_async_handler(func)
        return super().before(func)

    @classmethod
    def after(cls, func: Callable[..., Any]) -> Callable[..., Any]:
        _require_async_handler(func)
        return super().after(func)

    @classmethod
    def register(cls, func: Callable[..., Any]) -> None:
        _require_async_handler(func)
        super().register(func)

    @classmethod
    def register_before(cls, func: Callable[..., Any]) -> None:
        _require_async_handler(func)
        super().register_before(func)

    @classmethod
    def register_after(cls, func: Callable[..., Any]) -> None:
        _require_async_handler(func)
        super().register_after(func)

    @classmethod
    async def trigger(cls: type[T], *args: Any, **kwargs: Any) -> T:
        """在已有事件循环中跑完整条协程管线。"""
        return await cls._trigger_pipeline_async(*args, **kwargs)
