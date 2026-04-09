from __future__ import annotations
import logging
from typing import Any, ClassVar, TYPE_CHECKING
from abc import ABC
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr
from registry import Registry

if TYPE_CHECKING:
    from automation.hub import Hub

logger = logging.getLogger(__name__)

class BaseAutomation(BaseModel, ABC):
    model_config = ConfigDict(validate_assignment=True)

    _abstract: ClassVar[bool] = False
    _type: ClassVar[str]
    _registry: ClassVar[Registry]

    instance_name: str = Field(..., description="实例名")

    _IMMUTABLE_FIELDS: ClassVar[frozenset[str]] = frozenset({"instance_name"})
    _hub: Hub = PrivateAttr(default=None)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if cls.__dict__.get("_abstract", False):
            return
        if not hasattr(cls, "_type") or not isinstance(getattr(cls, "_type", None), str):
            raise TypeError(f"{cls.__name__} 必须定义 _type: ClassVar[str]")
        cls._registry.register(cls._type, cls)

    async def on_validate(self, hub: Hub) -> None:
        pass

    async def on_activate(self, hub: Hub) -> None:
        pass

    async def on_update(self, hub: Hub) -> None:
        pass

    async def on_start(self) -> None:
        pass

    async def on_stop(self) -> None:
        pass

    async def update(self, hub: Hub, new_spec: dict) -> None:
        for key, value in new_spec.items():
            if key in self._IMMUTABLE_FIELDS:
                continue
            if key in self.__class__.model_fields:
                setattr(self, key, value)
            else:
                logger.warning(
                    "%s.%s: ignoring unknown field %r",
                    self.__class__.__name__, self.instance_name, key,
                )