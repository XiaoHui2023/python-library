"""callback：用类型注解定义「载荷」，用 @子类 托管处理函数，再 trigger / atrigger 执行并取回同一实例读状态。

用法概要：
- 子类用注解声明字段（不含 ClassVar、不以 _ 开头）；同步默认，异步子类设 ``_async = True``。
- ``@MyCb`` 注册 ``def h(cb: MyCb)`` 或 ``def h()``；处理函数里通常就地修改 ``cb`` 的字段。
- ``MyCb.trigger(**kw)`` 会阻塞到所有同步处理结束；``await MyCb.atrigger(**kw)`` 用于异步处理。
- 返回值为本次触发的 ``MyCb`` 实例，用于读取更新后的字段。
"""
from __future__ import annotations
from typing import ClassVar, Callable, TypeVar, get_origin
import asyncio
import logging
import inspect
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
T = TypeVar("T", bound="Callback")

class Callback():
    """
    回调基类：注解字段为载荷；注册函数在 trigger 时并发执行；返回的实例可被读取/被 handler 修改。

    定义结构（字段即构造 ``trigger`` 的参数）::
        class A(Callback):
            attr: type

    触发（同步会等到全部注册函数结束；异步需 ``_async = True`` 且用 ``atrigger``）::
        cb = A.trigger(attr=value)
        cb = await A.atrigger(attr=value)

    注册处理函数（子类作装饰器；签名可 ``(cb: A)`` 或 ``()``）::
        @A
        def func(cb: A) -> None: ...

    实现要点：同步 ``trigger`` 使用线程池并等待完成；无注册函数时仍会构造并返回实例。
    """
    function_registry: ClassVar[dict[str, list[Callable]]] = {}
    """注册的函数列表"""
    _async: ClassVar[bool] = False
    """是否异步"""

    def __new__(cls, *args, **kwargs):
        """支持把 Callback 子类直接当装饰器使用"""
        if len(args) == 1 and not kwargs and callable(args[0]):
            func = args[0]
            if cls._async != asyncio.iscoroutinefunction(func):
                raise ValueError(
                    f"函数{func}是{'异步' if asyncio.iscoroutinefunction(func) else '同步'}，"
                    f"但回调{cls.__name__}是{'异步' if cls._async else '同步'}"
                )
            cls.register(func)
            return func
        return super().__new__(cls)

    def __init__(self, *args, **kwargs):
        """初始化事件实例"""
        field_names = self.__class__._field_names()
        for i, arg in enumerate(args):
            if i < len(field_names):
                setattr(self, field_names[i], arg)
            else:
                raise ValueError(f"参数过多[{i}]: {arg}")
        for key, value in kwargs.items():
            if key in field_names:
                setattr(self, key, value)
            else:
                raise ValueError(f"未知属性[{key}]: {value}")

    @classmethod
    def register(cls, func: Callable):
        """注册函数"""
        try:
            if cls.__name__ not in cls.function_registry:
                cls.function_registry[cls.__name__] = []
            if func not in cls.function_registry[cls.__name__]:
                cls.function_registry[cls.__name__].append(func)
        except Exception as e:
            logger.exception(f"注册函数{func}失败: {e}")
            raise e

    @classmethod
    def trigger(cls:type[T],*args,**kwargs) -> T:
        """同步触发回调"""
        try:
            self = cls(*args, **kwargs)

            self.before_trigger()
            funcs = cls.function_registry.get(cls.__name__, [])
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(self._call_registered, func, self) for func in funcs]
                for future in futures:
                    future.result()
            self.after_trigger()

            return self
        except Exception as e:
            logger.exception(f"触发回调{cls}失败: {e}")
            raise e

    @classmethod
    async def atrigger(cls:type[T],*args,**kwargs) -> T:
        """异步触发回调"""
        try:
            self = cls(*args, **kwargs)

            await self.before_atrigger()
            funcs = cls.function_registry.get(cls.__name__, [])
            tasks = [self._acall_registered(func, self) for func in funcs]
            if tasks:
                await asyncio.gather(*tasks)
            await self.after_atrigger()

            return self
        except Exception as e:
            logger.exception(f"异步触发回调{cls}失败: {e}")
            raise e

    def before_trigger(self) -> None:
        """同步触发前钩子"""
        pass

    async def before_atrigger(self) -> None:
        """异步触发前钩子"""
        pass

    def after_trigger(self) -> None:
        """同步触发后钩子"""
        pass

    async def after_atrigger(self) -> None:
        """异步触发后钩子"""
        pass

    @staticmethod
    def _call_registered(func: Callable, cb: "Callback"):
        """同步调用注册的函数，支持不传参数"""
        try:
            sig = inspect.signature(func)
        except (TypeError, ValueError):
            return func(cb)

        params = list(sig.parameters.values())
        positional = [
            p for p in params
            if p.kind in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
        has_varargs = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params)

        if has_varargs or len(positional) >= 1:
            return func(cb)
        return func()

    @staticmethod
    async def _acall_registered(func: Callable, cb: "Callback"):
        """异步调用注册的函数，支持不传参数"""
        try:
            sig = inspect.signature(func)
        except (TypeError, ValueError):
            return await func(cb)

        params = list(sig.parameters.values())
        positional = [
            p for p in params
            if p.kind in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
        has_varargs = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params)

        if has_varargs or len(positional) >= 1:
            return await func(cb)
        return await func()

    @classmethod
    def get_all(cls) -> list[type[Callback]]:
        """获取所有回调"""
        return list(cls.__subclasses__())

    @classmethod
    def _field_names(cls) -> list[str]:
        merged: dict[str, object] = {}
        for base in reversed(cls.__mro__):
            if base is object or base is Callback:
                # 跳过 object 和框架基类 Callback 本身
                continue

            # 把 postponed annotations 的字符串还原成真实类型
            annotations = inspect.get_annotations(base, eval_str=True)

            for name, tp in annotations.items():
                if name.startswith("_"):
                    continue
                if get_origin(tp) is ClassVar:
                    continue
                merged[name] = tp

        return list(merged.keys())

__all__ = [
    "Callback",
]