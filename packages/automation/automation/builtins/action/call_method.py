from __future__ import annotations

import inspect
from typing import Any

from pydantic import Field

from automation.core.action import Action
from automation.core.renderer import Renderer


class CallMethodAction(Action):
    """调用某实体上的方法。"""

    entity: str = Field(description="实体实例名，对应 context.entities 的键。")
    method: str = Field(description="实体上的方法名。")
    args: dict[str, Any] = Field(
        default_factory=dict,
        description="传给实体方法的命名参数；字符串值在运行期经渲染器求值。",
    )

    @property
    def display_label(self) -> str:
        return "call_method"

    @property
    def log_params(self) -> dict[str, Any]:
        return {"entity": self.entity, "method": self.method, "args": self.args}

    async def execute(self, renderer: Renderer) -> None:
        entities = self._ctx.entities
        if self.entity not in entities:
            raise ValueError(f"Entity {self.entity!r} not found")
        target = entities[self.entity]
        if not hasattr(target, self.method):
            raise ValueError(
                f"Entity {self.entity!r} has no method {self.method!r}"
            )
        fn = getattr(target, self.method)
        if not callable(fn):
            raise ValueError(
                f"Entity {self.entity!r}.{self.method} is not callable"
            )
        rendered_args = {
            key: renderer(value) if isinstance(value, str) else value
            for key, value in self.args.items()
        }
        result = fn(**rendered_args)
        if inspect.isawaitable(result):
            await result
