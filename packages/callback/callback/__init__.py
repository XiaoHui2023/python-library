from __future__ import annotations

import asyncio
import inspect
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, ClassVar, TypeVar, get_origin

from pydantic import BaseModel, ConfigDict
from pydantic._internal._model_construction import ModelMetaclass

logger = logging.getLogger(__name__)
T = TypeVar("T", bound="Callback")


def _annotation_is_classvar(tp: object) -> bool:
    """Whether ``tp`` is a :class:`typing.ClassVar` annotation (resolved or postponed string)."""
    if isinstance(tp, str):
        s = tp.strip()
        return (
            s.startswith("ClassVar[")
            or s.startswith("typing.ClassVar[")
            or s.startswith("typing_extensions.ClassVar[")
        )
    return get_origin(tp) is ClassVar


class CallbackMeta(ModelMetaclass):
    """构建模型前从类体 ``__annotations__`` 中移除「单下划线前缀且非 ClassVar」的名字。

    这样 ``_x: int`` 仅作类型检查约定、不参与载荷与校验；``_async: ClassVar[bool]`` 等仍保留。
    """

    def __new__(
        mcs,
        cls_name: str,
        bases: tuple[type[Any], ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> type:
        ann = namespace.get("__annotations__")
        if ann:
            filtered = {
                k: v
                for k, v in ann.items()
                if (not k.startswith("_")) or _annotation_is_classvar(v)
            }
            namespace = {**namespace, "__annotations__": filtered}
        return super().__new__(mcs, cls_name, bases, namespace, **kwargs)


class Callback(BaseModel, metaclass=CallbackMeta):
    """
    回调基类：基于 Pydantic :class:`~pydantic.BaseModel`，注解字段为载荷；注册函数在 ``trigger`` 时并发执行；返回的实例可被读取、被 handler 修改。

    定义结构（字段即构造 ``trigger`` 的参数）。可从 ``pydantic`` 导入 ``Field`` 描述默认值与说明等::

        from pydantic import Field

        class A(Callback):
            attr: str = Field(default="x", description="...")

    触发（同步会等到全部注册函数结束；异步需 ``_async = True`` 且用 ``atrigger``）::

        cb = A.trigger(attr=value)
        cb = await A.atrigger(attr=value)

    注册处理函数（子类作装饰器；签名可 ``(cb: A)`` 或 ``()``）::

        @A
        def func(cb: A) -> None: ...

    同一函数对象若再次 ``@A`` 注册，不会重复加入列表，触发时该函数只执行一次（不同函数则各执行一次）。

    实现要点：同步 ``trigger`` 使用线程池并等待完成；无注册函数时仍会构造并返回实例。实例化经 Pydantic 校验与默认值处理。
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    function_registry: ClassVar[dict[str, list[Callable]]] = {}
    """注册的函数列表"""
    _async: ClassVar[bool] = False
    """是否异步"""

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
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

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        cls = self.__class__
        field_names = cls._field_names()
        merged: dict[str, Any] = {}
        for i, arg in enumerate(args):
            if i < len(field_names):
                merged[field_names[i]] = arg
            else:
                raise ValueError(f"参数过多[{i}]: {arg}")
        for key, value in kwargs.items():
            if key in field_names:
                merged[key] = value
            else:
                raise ValueError(f"未知属性[{key}]: {value}")
        # 前向引用等导致模型未完成定义时，校验器不可用；与旧版 Callback 一致仅做字段赋值
        if not cls.__pydantic_complete__:
            tmp = cls.model_construct(**merged)
            self.__dict__.update(tmp.__dict__)
            object.__setattr__(self, "__pydantic_fields_set__", tmp.__pydantic_fields_set__)
            object.__setattr__(self, "__pydantic_extra__", tmp.__pydantic_extra__)
            priv = tmp.__pydantic_private__
            if priv is not None:
                object.__setattr__(self, "__pydantic_private__", priv)
            return
        super().__init__(**merged)

    @classmethod
    def register(cls, func: Callable):
        """注册函数；同一 ``func`` 对象不会重复加入。"""
        try:
            if cls.__name__ not in cls.function_registry:
                cls.function_registry[cls.__name__] = []
            if func not in cls.function_registry[cls.__name__]:
                cls.function_registry[cls.__name__].append(func)
        except Exception as e:
            logger.exception(f"注册函数{func}失败: {e}")
            raise e

    @classmethod
    def trigger(cls: type[T], *args: Any, **kwargs: Any) -> T:
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
    async def atrigger(cls: type[T], *args: Any, **kwargs: Any) -> T:
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
            p
            for p in params
            if p.kind
            in (
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
            p
            for p in params
            if p.kind
            in (
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
            if base is object or base is Callback or base is BaseModel:
                continue

            annotations = inspect.get_annotations(base, eval_str=False)

            for name, tp in annotations.items():
                if name.startswith("_"):
                    continue
                if _annotation_is_classvar(tp):
                    continue
                merged[name] = tp

        return list(merged.keys())


__all__ = [
    "Callback",
]
