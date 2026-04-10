from __future__ import annotations
from typing import Any, ClassVar, TYPE_CHECKING
from pydantic import Field, PrivateAttr
from automation.core import Entity
from automation.core.entity import AttributeInfo

if TYPE_CHECKING:
    from automation.hub import Hub

TYPE_MAP = {"int": int, "float": float, "str": str, "bool": bool}


class VariableEntity(Entity):
    _abstract: ClassVar[bool] = False
    _type: ClassVar[str] = "variable"

    properties: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="变量定义：{name: {type: str, default: value}}",
    )

    _values: dict[str, Any] = PrivateAttr(default_factory=dict)

    async def on_validate(self, hub: Hub) -> None:
        for name, spec in self.properties.items():
            type_name = spec.get("type", "str")
            default = spec.get("default")
            if type_name == "entity_list":
                names = default or []
                for n in names:
                    if n not in hub.entities:
                        raise ValueError(
                            f"Entity {n!r} not found for property {name!r}"
                        )
                self._values[name] = [hub.entities[n] for n in names]
            elif type_name == "list":
                self._values[name] = list(default) if default else []
            else:
                self._values[name] = self._cast(type_name, default)

    def get_attributes(self) -> tuple[AttributeInfo, ...]:
        return tuple(
            AttributeInfo(
                name=name,
                type=spec.get("type", "str"),
                description=spec.get("description", ""),
                readonly=spec.get("type") == "entity_list",
                default=spec.get("default"),
            )
            for name, spec in self.properties.items()
        )

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
            if type_name == "entity_list":
                raise AttributeError(
                    f"Property {name!r} is read-only (entity_list)"
                )
            if type_name == "list":
                priv["_values"][name] = list(value) if not isinstance(value, list) else value
                return
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