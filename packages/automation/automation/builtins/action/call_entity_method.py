from __future__ import annotations
import inspect
from typing import ClassVar, TYPE_CHECKING

from pydantic import Field, PrivateAttr
from automation.core import Action, Entity

if TYPE_CHECKING:
    from automation.hub import Hub


class CallEntityMethod(Action):
    _abstract: ClassVar[bool] = False
    _type: ClassVar[str] = "call_entity_method"

    entity: str = Field(description="实体名称")
    method: str = Field(description="方法名称")
    args: dict = Field(default_factory=dict, description="方法参数")

    _entity: Entity | None = PrivateAttr(default=None)

    async def on_validate(self, hub: Hub) -> None:
        try:
            entity = hub.entities[self.entity]
        except KeyError as e:
            raise ValueError(f"Entity {self.entity!r} not found") from e

        if not hasattr(entity, self.method):
            raise ValueError(
                f"Entity {self.entity!r} has no method {self.method!r}"
            )

        method = getattr(entity, self.method)
        if not callable(method):
            raise ValueError(
                f"Entity {self.entity!r}.{self.method} is not callable"
            )

        try:
            inspect.signature(method).bind(**self.args)
        except TypeError as e:
            raise ValueError(
                f"Invalid arguments for {self.entity!r}.{self.method}()"
            ) from e

        self._entity = entity

    async def run(self) -> None:
        if self._entity is None:
            raise RuntimeError(
                f"Action {self.instance_name!r} not initialized; call on_validate() first"
            )
        method = getattr(self._entity, self.method)
        result = method(**self.args)
        if inspect.isawaitable(result):
            await result