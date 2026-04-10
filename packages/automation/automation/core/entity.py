from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, ClassVar

from .base import BaseAutomation
from registry import Registry

NAME_SPACE = "entity"

entity_registry = Registry(NAME_SPACE)


@dataclass(frozen=True)
class AttributeInfo:
    """Entity 暴露给配置/脚本使用的属性描述"""
    name: str
    type: str
    description: str = ""
    readonly: bool = False
    default: Any = None


@dataclass(frozen=True)
class MethodInfo:
    """Entity 暴露给配置使用的方法描述"""
    name: str
    description: str = ""
    params: dict[str, str] = field(default_factory=dict)


class Entity(BaseAutomation):
    _abstract: ClassVar[bool] = True
    _registry: ClassVar[Registry] = entity_registry

    _attributes: ClassVar[tuple[AttributeInfo, ...]] = ()
    _methods: ClassVar[tuple[MethodInfo, ...]] = ()

    def get_attributes(self) -> tuple[AttributeInfo, ...]:
        """运行时属性列表，子类可重写以支持动态属性（如 VariableEntity）"""
        return self._attributes

    def get_methods(self) -> tuple[MethodInfo, ...]:
        return self._methods

    def get_attribute_values(self) -> dict[str, Any]:
        return {
            attr.name: getattr(self, attr.name, None)
            for attr in self.get_attributes()
        }