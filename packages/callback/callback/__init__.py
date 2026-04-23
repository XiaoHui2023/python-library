from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Callable
from typing import Any, ClassVar, TypeVar, get_origin

from pydantic import BaseModel, ConfigDict
from pydantic._internal._model_construction import ModelMetaclass

from callback.registry import CallbackLayers

logger = logging.getLogger(__name__)
T = TypeVar("T", bound="Callback")


def _annotation_is_classvar(tp: object) -> bool:
    """供元类判断某注解是否表示类变量，从而不把其名字当作载荷字段。"""
    if isinstance(tp, str):
        s = tp.strip()
        return (
            s.startswith("ClassVar[")
            or s.startswith("typing.ClassVar[")
            or s.startswith("typing_extensions.ClassVar[")
        )
    return get_origin(tp) is ClassVar


class CallbackMeta(ModelMetaclass):
    """在 Pydantic 建表前裁剪类体注解，使只做类型约定的名字不参与载荷校验。

    对子类做「类调用」时：单参且为可调用对象且无关键字参数时走中间层登记；否则走同步触发并返回管线结束后的实例。
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

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        """`子类(可调用对象)` 等价于 `register`；其余参数形态等价于同步 `trigger`。"""
        if len(args) == 1 and not kwargs and callable(args[0]):
            func = args[0]
            cls.register(func)
            return func
        return cls.trigger(*args, **kwargs)


class Callback(BaseModel, metaclass=CallbackMeta):
    """带分层登记的载荷模型：注解字段描述一次调用的数据，监听者按前中后三层登记在类型上并顺序触发。

    基类仅作字段形态与类方法协议的公共入口，不挂载分层登记；请定义具体子类，并在子类上登记与触发。

    子类在创建时会挂上私有登记容器；前、后两层的装饰器由类方法 `before` / `after` 显式提供，中间层仍可用 `@子类` 或 `register`。
    `子类(...)` 等价于同步触发并返回管线结束后的同一条实例。
    登记可同时包含普通函数与协程（内部仍用 asyncio 调度）。
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """为子类准备私有分层登记容器（`_layers`）。"""
        super().__init_subclass__(**kwargs)
        if "_layers" not in cls.__dict__:
            cls._layers = CallbackLayers()

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
    def _cb_layers(cls) -> CallbackLayers:
        """运行期子类上必有 `_layers`；基类未挂载容器时给出明确错误。"""
        if "_layers" not in cls.__dict__:
            name = cls.__name__
            raise TypeError(
                f"{name} 未挂载分层登记，请在继承 Callback 的具体子类上登记或触发，勿在 Callback 基类上调用。",
            )
        return cls.__dict__["_layers"]

    @classmethod
    def before(cls, func: Callable[..., Any]) -> Callable[..., Any]:
        """前层装饰器，与 `register_before` 同一套登记与去重规则；登记后仍返回被装饰的函数。"""
        cls._cb_layers().before.register(func)
        return func

    @classmethod
    def after(cls, func: Callable[..., Any]) -> Callable[..., Any]:
        """后层装饰器，与 `register_after` 同一套登记与去重规则；登记后仍返回被装饰的函数。"""
        cls._cb_layers().after.register(func)
        return func

    @classmethod
    def register(cls, func: Callable[..., Any]) -> None:
        """向中间层登记处理函数；与仅把子类型当作装饰器使用时的语义相同。"""
        cls._cb_layers().middle.register(func)

    @classmethod
    def register_before(cls, func: Callable[..., Any]) -> None:
        """向最先执行的一层登记处理函数。"""
        cls._cb_layers().before.register(func)

    @classmethod
    def register_after(cls, func: Callable[..., Any]) -> None:
        """向最后执行的一层登记处理函数。"""
        cls._cb_layers().after.register(func)

    @classmethod
    def clear_layer_registries(cls) -> None:
        """清空从本类型出发整棵子类树上的分层登记，供测试或进程内重置。"""
        stack: list[type[Any]] = list(cls.__subclasses__())
        while stack:
            c = stack.pop()
            stack.extend(c.__subclasses__())
            reg = c.__dict__.get("_layers")
            if reg is not None:
                reg.clear()

    @classmethod
    async def _trigger_pipeline_async(cls: type[T], *args: Any, **kwargs: Any) -> T:
        """层顺序为前、中、后；每层内并发，整层结束后再进下一层。

        同一层里协程与普通可调用对象可混登记：协程在本层并发收尾，普通函数在线程里执行，避免占满事件循环。
        """
        try:
            self = object.__new__(cls)
            cls.__init__(self, *args, **kwargs)
            for funcs in cls._cb_layers().tier_lists_in_order():
                if not funcs:
                    continue
                tasks = [cls._acall_registered(func, self) for func in funcs]
                await asyncio.gather(*tasks)
            return self
        except Exception as e:
            logger.exception(f"触发回调{cls}失败: {e}")
            raise e

    @classmethod
    def trigger(cls: type[T], *args: Any, **kwargs: Any) -> T:
        """同步触发入口：当前线程无正在运行的事件循环时，内部用 asyncio.run 跑完整条管线。

        若已在事件循环中（例如在 async def 里），无法在此线程上阻塞式触发；请从普通同步上下文调用，
        或另起线程并在该线程内调用 trigger。
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(cls._trigger_pipeline_async(*args, **kwargs))
        msg = (
            f"已在运行中的事件循环内无法调用 {cls.__name__}.trigger()；"
            f"请从非事件循环线程触发，或在线程中执行 {cls.__name__}.trigger(...)。"
        )
        raise RuntimeError(msg)

    @staticmethod
    def _call_registered(func: Callable[..., Any], cb: Callback) -> Any:
        """调用已登记的处理函数：是否把当前载荷实例传入由可调用对象的参数形态决定。"""
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
    async def _acall_registered(func: Callable[..., Any], cb: Callback) -> Any:
        """单次触发调用：协程走异步收尾；普通函数在线程里执行，是否传入载荷由可调用对象的参数形态决定。"""
        if not asyncio.iscoroutinefunction(func):
            return await asyncio.to_thread(Callback._call_registered, func, cb)
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
        """列出从本类型直接派生的子类型。"""
        return list(cls.__subclasses__())

    @classmethod
    def _field_names(cls) -> list[str]:
        """沿继承链汇总参与构造与校验的字段名，排除类变量与下划线开头的约定名。"""
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
