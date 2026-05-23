from __future__ import annotations

from typing import Any

from pydantic import Field

from automation.core.action import Action
from automation.core.renderer import Renderer


class SetAttributeAction(Action):
    """设置某实体上的属性值。"""

    entity: str = Field(description="实体实例名，对应 context.entities 的键。")
    attribute: str = Field(description="实体上的属性名。")
    value: Any = Field(description="要写入的值；字符串在运行期经渲染器求值。")

    @property
    def display_label(self) -> str:
        return "set_attribute"

    @property
    def log_params(self) -> dict[str, Any]:
        return {
            "entity": self.entity,
            "attribute": self.attribute,
            "value": self.value,
        }

    async def execute(self, renderer: Renderer) -> None:
        entities = self._ctx.entities
        if self.entity not in entities:
            raise ValueError(f"Entity {self.entity!r} not found")
        target = entities[self.entity]
        if not hasattr(target, self.attribute):
            raise ValueError(
                f"Entity {self.entity!r} has no attribute {self.attribute!r}"
            )
        value = self.value
        if isinstance(value, str):
            value = renderer(value)
        setattr(target, self.attribute, value)
