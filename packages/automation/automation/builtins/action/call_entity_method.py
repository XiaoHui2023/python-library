from __future__ import annotations
import inspect
from typing import ClassVar, TYPE_CHECKING
from pydantic import Field
from automation.core import Action

if TYPE_CHECKING:
    from automation.renderer import Renderer


class CallEntityMethod(Action):
    _abstract: ClassVar[bool] = False
    _type: ClassVar[str] = "call_entity_method"

    entity: str = Field(description="实体名称")
    method: str = Field(description="方法名称")
    args: dict = Field(default_factory=dict, description="方法参数")

    async def execute(self, renderer: Renderer) -> None:
        hub = renderer._hub
        if self.entity not in hub.entities:
            raise ValueError(f"Entity {self.entity!r} not found")
        entity = hub.entities[self.entity]
        if not hasattr(entity, self.method):
            raise ValueError(
                f"Entity {self.entity!r} has no method {self.method!r}"
            )
        method = getattr(entity, self.method)
        if not callable(method):
            raise ValueError(
                f"Entity {self.entity!r}.{self.method} is not callable"
            )
        result = method(**self.args)
        if inspect.isawaitable(result):
            await result