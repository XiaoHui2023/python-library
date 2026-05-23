from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any

from pydantic import BaseModel, Field
from automation.listener.events import EventFired

from .base import BaseAutomation

logger = logging.getLogger(__name__)


class EventContext(BaseModel):
    """事件触发时的上下文。"""

    event_name: str = Field(description="当前自动化事件实例名，用于分发与条件求值")
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="并入条件表达式与回调的扁平键值",
    )

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


class Event(BaseAutomation):
    """自动化事件：满足条件后依次调用已注册的回调。

    具体触发路径由 builtins 中的派生类型补充。
    """

    conditions: list[str] = Field(
        default_factory=list,
        description="条件表达式列表，全部满足才触发事件",
    )

    async def on_validate(self) -> None:
        for expr in self.conditions:
            self._ctx.create_renderer()(expr)

    async def on_activate(self) -> None:
        self._ctx.ensure_observer_global_after()

    async def fire(
        self,
        data: dict[str, Any] | EventContext | None = None,
    ) -> None:
        """按条件触发监听；本次附加数据由参数直接给出。

        Args:
            data: 并入条件与回调的键值，或已是事件上下文；省略表示无附加数据。
        """

        if isinstance(data, EventContext):
            context = data.model_copy(update={"event_name": self.instance_name})
        elif data is not None:
            context = EventContext(event_name=self.instance_name, data=dict(data))
        else:
            context = EventContext(event_name=self.instance_name, data={})

        if self.conditions:
            renderer = self._ctx.create_renderer().derive(context.data)
            for expr in self.conditions:
                if not bool(renderer(expr)):
                    return

        self._ctx.emit(
            EventFired(self.instance_name, data=dict(context.data))
        )

        handlers = self._ctx.get_event_fire_handlers(self.instance_name)
        tasks: list[Any] = []
        for callback in handlers:
            try:
                result = callback(context)
            except Exception as e:
                logger.error("Event callback failed: %s", e, exc_info=True)
                continue
            if inspect.isawaitable(result):
                tasks.append(result)
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.error(
                        "Event async callback failed: %s", result, exc_info=result
                    )


__all__ = [
    "Event",
    "EventContext",
]
