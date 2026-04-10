from __future__ import annotations
from typing import Any, ClassVar, TYPE_CHECKING
from pydantic import Field
from automation.core import Action

if TYPE_CHECKING:
    from automation.renderer import Renderer


class SetAttributeAction(Action):
    _abstract: ClassVar[bool] = False
    _type: ClassVar[str] = "set_attribute"

    entity: str = Field(description="实体名称")
    attribute: str = Field(description="属性名称")
    value: Any = Field(description="新值")

    async def execute(self, renderer: Renderer) -> None:
        hub = renderer._hub
        if self.entity not in hub.entities:
            raise ValueError(f"Entity {self.entity!r} not found")
        entity = hub.entities[self.entity]
        if not hasattr(entity, self.attribute):
            raise ValueError(
                f"Entity {self.entity!r} has no attribute {self.attribute!r}"
            )
        setattr(entity, self.attribute, self.value)