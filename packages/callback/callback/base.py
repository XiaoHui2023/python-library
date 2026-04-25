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
T = TypeVar("T", bound="CallbackBase")


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


class _CallbackPydanticMeta(ModelMetaclass):
    """在 Pydantic 建表前裁剪类体注解，使只做类型约定的名字不参与载荷校验。"""

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


class CallbackBase(BaseModel, metaclass=_CallbackPydanticMeta):
    """带分层登记的载荷模型：字段描述一次调用的数据，监听者按前中后三层登记在类型上并顺序触发。

    本类型为包内基类，对外请继承同步根或异步根类型，在子类上按根类型要求登记，再触发；勿在本类型上直接登记。
    前、后两层的装饰器由子类类方法 `before` / `after` 显式提供，中间层用子类作装饰器或 `register`。
    根类型决定处理函数是仅同步 def 或仅 `async def`，与触发入口一致。
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.__dict__.get("__callback_is_root__"):
            return
        if "_layers" not in cls.__dict__:
            cls._layers = CallbackLayers()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        c = self.__class__
        field_names = c._field_names()
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
        if not c.__pydantic_complete__:
            tmp = c.model_construct(**merged)
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
        """运行期子类上必有 `_layers`；基类或根类型未挂容器时给出明确错误。"""
        if "_layers" not in cls.__dict__:
            name = cls.__name__
            raise TypeError(
                f"{name} 未挂载分层登记，请在继承同步或异步根类型的具体子类上登记或触发，勿在根类型上调用。",
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
        """层顺序为前、中、后；同一层内多个协程并发，整层结束后再进下一层。异步根上登记的处理函数须均为协程。"""
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

    @staticmethod
    def _call_registered(func: Callable[..., Any], cb: CallbackBase) -> Any:
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
    async def _acall_registered(func: Callable[..., Any], cb: CallbackBase) -> Any:
        """异步路径单次调用；是否把载荷当参数由目标协程的签名决定。"""
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
    def get_all(cls) -> list[type[CallbackBase]]:
        """列出从本类型直接派生的子类型。"""
        return list(cls.__subclasses__())

    @classmethod
    def _field_names(cls) -> list[str]:
        """沿继承链汇总参与构造与校验的字段名，排除类变量与下划线开头的约定名。"""
        merged: dict[str, object] = {}
        for mro_cls in reversed(cls.__mro__):
            if mro_cls is object or mro_cls is CallbackBase or mro_cls is BaseModel:
                continue
            if mro_cls.__dict__.get("__callback_is_root__"):
                continue

            annotations = inspect.get_annotations(mro_cls, eval_str=False)

            for name, tp in annotations.items():
                if name.startswith("_"):
                    continue
                if _annotation_is_classvar(tp):
                    continue
                merged[name] = tp

        return list(merged.keys())
