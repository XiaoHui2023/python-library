from __future__ import annotations

import inspect
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, ClassVar, TypeVar

from callback.base import CallbackBase, _CallbackPydanticMeta

logger = logging.getLogger(__name__)


def _require_sync_handler(func: Callable[..., Any]) -> None:
    if inspect.iscoroutinefunction(func):
        raise TypeError(
            "继承 Callback 的子类只登记普通 def；协程请使用继承 AsyncCallback 的子类。",
        )


class _SyncCallbackMeta(_CallbackPydanticMeta):
    """对子类做类调用时：单参可调用走登记校验，否则走同步 `trigger`。"""

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if len(args) == 1 and not kwargs and callable(args[0]):
            func = args[0]
            cls.register(func)
            return func
        return cls.trigger(*args, **kwargs)


S = TypeVar("S", bound="Callback")


class Callback(CallbackBase, metaclass=_SyncCallbackMeta):
    """同步根：触发全程不用事件循环，只跑同步 def；多路同层时在线程池里并行。"""

    __callback_is_root__: ClassVar[bool] = True

    @classmethod
    def before(cls, func: Callable[..., Any]) -> Callable[..., Any]:
        _require_sync_handler(func)
        return super().before(func)

    @classmethod
    def after(cls, func: Callable[..., Any]) -> Callable[..., Any]:
        _require_sync_handler(func)
        return super().after(func)

    @classmethod
    def register(cls, func: Callable[..., Any]) -> None:
        _require_sync_handler(func)
        super().register(func)

    @classmethod
    def register_before(cls, func: Callable[..., Any]) -> None:
        _require_sync_handler(func)
        super().register_before(func)

    @classmethod
    def register_after(cls, func: Callable[..., Any]) -> None:
        _require_sync_handler(func)
        super().register_after(func)

    @classmethod
    def _trigger_pipeline_sync(cls: type[S], *args: Any, **kwargs: Any) -> S:
        try:
            self = object.__new__(cls)
            cls.__init__(self, *args, **kwargs)
            for funcs in cls._cb_layers().tier_lists_in_order():
                if not funcs:
                    continue
                if len(funcs) == 1:
                    CallbackBase._call_registered(funcs[0], self)
                else:
                    with ThreadPoolExecutor(max_workers=len(funcs)) as ex:
                        futs = [
                            ex.submit(CallbackBase._call_registered, f, self)
                            for f in funcs
                        ]
                        for fut in as_completed(futs):
                            fut.result()
            return self
        except Exception as e:
            logger.exception(f"触发回调{cls}失败: {e}")
            raise e

    @classmethod
    def trigger(cls: type[S], *args: Any, **kwargs: Any) -> S:
        """在此线程上顺序跑前中后三层；同层多函数用线程池并行。不使用 asyncio、不要求事件循环。"""
        return cls._trigger_pipeline_sync(*args, **kwargs)
