from __future__ import annotations
from typing import Any, ClassVar
from pydantic import Field, PrivateAttr
from automation.core import Entity
from automation.core.entity import AttributeInfo

TYPE_MAP = {"int": int, "float": float, "str": str, "bool": bool}


class VariableEntity(Entity):
    _abstract: ClassVar[bool] = False
    _type: ClassVar[str] = "variable"

    properties: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="变量定义：{name: {type: str, default: value}}",
    )

    _values: dict[str, Any] = PrivateAttr(default_factory=dict)

    async def on_validate(self, hub) -> None:
        for name, spec in self.properties.items():
            type_name = spec.get("type", "str")
            default = spec.get("default")
            self._values[name] = self._cast(type_name, default)

    def get_attributes(self) -> tuple[AttributeInfo, ...]:
        dynamic = tuple(
            AttributeInfo(
                name=name,
                type=spec.get("type", "str"),
                description=spec.get("description", ""),
                readonly=False,
                default=spec.get("default"),
            )
            for name, spec in self.properties.items()
        )
        return dynamic

    def __getattr__(self, name: str) -> Any:
        if not name.startswith("_"):
            priv = self.__dict__.get("__pydantic_private__")
            if priv and "_values" in priv and name in priv["_values"]:
                return priv["_values"][name]
        return super().__getattr__(name)

    def __setattr__(self, name: str, value: Any) -> None:
        priv = self.__dict__.get("__pydantic_private__")
        if priv is not None and "_values" in priv and name in priv["_values"]:
            type_name = self.properties[name].get("type", "str")
            priv["_values"][name] = self._cast(type_name, value)
            return
        super().__setattr__(name, value)

    @staticmethod
    def _cast(type_name: str, value: Any) -> Any:
        if value is None:
            return None
        caster = TYPE_MAP.get(type_name)
        if caster is not None:
            return caster(value)
        return value