from __future__ import annotations
from dataclasses import dataclass, field
import inspect
from typing import Any

from pydantic import BaseModel
from .base import BaseAutomation
from abc import ABC

_BASE_CLASSES = frozenset({BaseAutomation, BaseModel, ABC, object})

@dataclass(frozen=True)
class AttributeInfo:
    """属性信息"""
    name: str
    """属性名称"""
    type: str = "Any"
    """属性类型"""
    description: str = ""
    """属性描述"""
    readonly: bool = False
    """是否只读"""
    default: Any = None
    """默认值"""

@dataclass(frozen=True)
class MethodInfo:
    """方法信息"""
    name: str
    """方法名称"""
    description: str = ""
    """方法描述"""
    params: dict[str, str] = field(default_factory=dict)
    """方法参数"""
    return_type: str = "None"
    """返回类型"""

@dataclass(frozen=True)
class CallInfo:
    """一次方法被观测到后的简要信息。"""

    instance_name: str
    """对象在配置中的名字"""

    instance_type: str
    """对象所属类型，便于区分同名方法来自哪个类"""

    method_name: str
    """被调用的方法名"""

    arguments: dict[str, object] = field(default_factory=dict)
    """调用传入的参数"""


@dataclass(frozen=True)
class AttributeWatchInfo:
    """实体某次属性写入时的过滤条件，空串表示该维度不过滤。"""

    entity_type: str = ""
    """实体实现选型键，空则匹配任意类型"""

    entity_name: str = ""
    """实体实例名，空则匹配任意实例"""

    attribute: str = ""
    """属性名，空则匹配任意属性"""


def _annotation_str(annotation: Any) -> str:
    if annotation is None or annotation is inspect.Parameter.empty:
        return "Any"
    if isinstance(annotation, str):
        return annotation
    return getattr(annotation, "__name__", str(annotation))


def introspect_attributes(cls: type[BaseModel]) -> tuple[AttributeInfo, ...]:
    """从类的 property 和 pydantic 字段自动提取属性信息"""
    attrs: list[AttributeInfo] = []
    seen: set[str] = set()

    for klass in cls.__mro__:
        if klass in _BASE_CLASSES:
            continue
        for name, obj in klass.__dict__.items():
            if name.startswith("_") or name in seen:
                continue
            seen.add(name)
            if isinstance(obj, property):
                fget = obj.fget
                ret = fget.__annotations__.get("return", "Any") if fget else "Any"
                attrs.append(AttributeInfo(
                    name=name,
                    type=_annotation_str(ret),
                    description=(fget.__doc__ or "").strip() if fget else "",
                    readonly=obj.fset is None,
                ))

    for name, fi in cls.model_fields.items():
        if name in seen or name == "instance_name":
            continue
        seen.add(name)
        attrs.append(AttributeInfo(
            name=name,
            type=_annotation_str(fi.annotation),
            description=fi.description or "",
            readonly=False,
            default=fi.default if not fi.is_required() else None,
        ))

    return tuple(attrs)


def introspect_methods(cls: type[BaseModel]) -> tuple[MethodInfo, ...]:
    """从类的公开方法自动提取方法信息"""
    methods: list[MethodInfo] = []
    seen: set[str] = set()

    # 获取 BaseAutomation 类中的基础方法
    basic_methods = frozenset(
        name
        for name, obj in BaseAutomation.__dict__.items()
        if not name.startswith("_")
        and not isinstance(obj, property)
        and callable(getattr(obj, "__func__", obj))
    )

    for klass in cls.__mro__:
        if klass in _BASE_CLASSES:
            continue
        for name, obj in klass.__dict__.items():
            if (
                name.startswith("_")
                or name in seen
                or isinstance(obj, property)
                or name in basic_methods
            ):
                continue
            seen.add(name)

            func = obj
            if isinstance(obj, staticmethod):
                func = obj.__func__
            elif isinstance(obj, classmethod):
                func = obj.__func__

            if not callable(func):
                continue
            if not hasattr(func, "__annotations__"):
                continue

            sig = inspect.signature(func)
            params: dict[str, str] = {}
            for pname, param in sig.parameters.items():
                if pname in ("self", "cls"):
                    continue
                type_str = _annotation_str(param.annotation)
                if param.default is not inspect.Parameter.empty:
                    type_str += f" = {param.default!r}"
                params[pname] = type_str

            ret = func.__annotations__.get("return")
            methods.append(MethodInfo(
                name=name,
                description=(func.__doc__ or "").strip(),
                params=params,
                return_type=_annotation_str(ret),
            ))

    return tuple(methods)