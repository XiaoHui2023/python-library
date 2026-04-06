from __future__ import annotations
from typing import ClassVar
from abc import ABC
from pydantic import BaseModel, Field
from registry import Registry

class BaseAutomation(BaseModel, ABC):
    _abstract: ClassVar[bool] = False
    _type: ClassVar[str]
    _registry: ClassVar[Registry]

    instance_name: str = Field(..., description="实例名")

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # 如果子类没有显式定义 _abstract，则认为不是抽象类
        if cls.__dict__.get("_abstract", False):
            return
        cls._registry.register(cls._type, cls)

    def validate(self, ctx) -> None:
        """只做校验，不产生副作用"""
        pass

    def activate(self, ctx) -> None:
        """在全部校验通过后再做绑定、副作用注册"""
        pass