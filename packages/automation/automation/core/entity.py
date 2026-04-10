from __future__ import annotations
import inspect
from abc import ABC
from dataclasses import dataclass, field
from typing import Any, ClassVar

from pydantic import BaseModel

from .base import BaseAutomation
from registry import Registry

NAME_SPACE = "entity"
entity_registry = Registry(NAME_SPACE)


@dataclass(frozen=True)
class AttributeInfo:
    name: str
    type: str = "Any"
    description: str = ""
    readonly: bool = False
    default: Any = None


@dataclass(frozen=True)
class MethodInfo:
    name: str
    description: str = ""
    params: dict[str, str] = field(default_factory=dict)
    return_type: str = "None"


# ── 内省工具函数 ──

_BASE_CLASSES = frozenset({BaseAutomation, BaseModel, ABC, object})

_LIFECYCLE_METHODS = frozenset({
    "on_validate", "on_activate", "on_update", "on_start", "on_stop",
    "update", "get_attributes", "get_methods", "get_attribute_values",
})


def _annotation_str(annotation: Any) -> str:
    if annotation is None or annotation is inspect.Parameter.empty:
        return "Any"
    if isinstance(annotation, str):
        return annotation
    return getattr(annotation, "__name__", str(annotation))


def introspect_attributes(cls: type) -> tuple[AttributeInfo, ...]:
    """从类的 property 和 pydantic 字段自动提取属性信息"""
    attrs: list[AttributeInfo] = []
    seen: set[str] = set()

    for klass in cls.__mro__:
        if klass in _BASE_CLASSES or klass is Entity:
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


def introspect_methods(cls: type) -> tuple[MethodInfo, ...]:
    """从类的公开方法自动提取方法信息"""
    methods: list[MethodInfo] = []
    seen: set[str] = set()

    for klass in cls.__mro__:
        if klass in _BASE_CLASSES or klass is Entity:
            continue
        for name, obj in klass.__dict__.items():
            if (
                name.startswith("_")
                or name in seen
                or name in _LIFECYCLE_METHODS
                or isinstance(obj, property)
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


# ── Entity 基类 ──

class Entity(BaseAutomation):
    _abstract: ClassVar[bool] = True
    _registry: ClassVar[Registry] = entity_registry

    def get_attributes(self) -> tuple[AttributeInfo, ...]:
        return introspect_attributes(type(self))

    def get_methods(self) -> tuple[MethodInfo, ...]:
        return introspect_methods(type(self))

    def get_attribute_values(self) -> dict[str, Any]:
        return {
            attr.name: getattr(self, attr.name, None)
            for attr in self.get_attributes()
        }