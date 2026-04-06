from __future__ import annotations
from typing import ClassVar

from pydantic import Field, PrivateAttr
from automation.core.base import BaseAutomation
from automation.core.event import Event
from automation.core.condition import Condition
from automation.core.action import Action
from registry import Registry

NAME_SPACE = "trigger"

trigger_registry = Registry(NAME_SPACE)

class Trigger(BaseAutomation):
    _abstract: ClassVar[bool] = True
    _registry: ClassVar[Registry] = trigger_registry

    event: str = Field(description="事件名称")
    conditions: list[str] = Field(default_factory=list, description="条件名称列表")
    actions: list[str] = Field(default_factory=list, description="动作名称列表")

    _event: Event | None = PrivateAttr(default=None)
    _conditions: list[Condition] = PrivateAttr(default_factory=list)
    _actions: list[Action] = PrivateAttr(default_factory=list)

    def validate(self, ctx) -> None:
        try:
            self._event = ctx.events[self.event]
        except KeyError as e:
            raise ValueError(f"事件 {self.event!r} 不存在") from e

        try:
            self._conditions = [ctx.conditions[name] for name in self.conditions]
        except KeyError as e:
            raise ValueError(f"条件 {e.args[0]!r} 不存在") from e

        try:
            self._actions = [ctx.actions[name] for name in self.actions]
        except KeyError as e:
            raise ValueError(f"动作 {e.args[0]!r} 不存在") from e

        if not self._actions:
            raise ValueError("至少需要一个 action")

    def activate(self, ctx) -> None:
        self._event.on_fire(self.run)

    async def run(self):
        for condition in self._conditions:
            if not condition.check():
                return

        for action in self._actions:
            await action.run()