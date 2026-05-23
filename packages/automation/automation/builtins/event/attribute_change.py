from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field, PrivateAttr

from automation.core.base import BaseAutomation, registered_kind_for
from automation.core.event import EventContext
from automation.core.registry_catalog import event_registry
from automation.core.info import AttributeWatchInfo

from .on_call import OnCallEvent


class AttributeChangeEventData(EventContext):
    """由 on_changes 路径触发：结构化字段与并入条件的扁平 data 同源。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    event_name: str = Field(
        default="",
        description="激活 fire 时由 Event 填入本事件实例名；构造监听载荷时可省略",
    )
    entity: BaseAutomation = Field(description="发生写入的实体实例")
    attribute: str = Field(description="被写入的属性名")
    old: Any = Field(description="写入前的取值")
    new: Any = Field(description="写入后的取值")

    def as_payload(self) -> dict[str, Any]:
        """转成条件与回调使用的扁平表，实体仍以运行中实例传入。"""

        return {
            "entity": self.entity,
            "attribute": self.attribute,
            "old": self.old,
            "new": self.new,
        }


def _register_on_change_handlers(ev: Any) -> None:
    """按 on_changes 将异步 handler 登记到上下文的属性变更链。"""

    for h in ev._attribute_watch_handlers:
        try:
            ev._ctx._on_state_changed.remove(h)
        except ValueError:
            pass
    ev._attribute_watch_handlers.clear()

    for watch in ev.on_changes:

        async def handler(
            entity: Any,
            attr: str,
            old: Any,
            new: Any,
            *,
            _w: AttributeWatchInfo = watch,
            _ev: Any = ev,
        ) -> None:
            if _w.entity_type and registered_kind_for(type(entity)) != _w.entity_type:
                return
            if _w.entity_name and entity.instance_name != _w.entity_name:
                return
            if _w.attribute and attr != _w.attribute:
                return
            await _ev.fire(
                AttributeChangeEventData(
                    entity=entity,
                    attribute=attr,
                    old=old,
                    new=new,
                )
            )

        ev._ctx._on_state_changed.append(handler)
        ev._attribute_watch_handlers.append(handler)


class AttributeWatchEvent(OnCallEvent):
    """在基类事件之上登记 on_changes，从实体属性变更链触发 fire。"""

    on_changes: list[AttributeWatchInfo] = Field(
        default_factory=list,
        description="实体属性变更时按条过滤后触发本事件，空列表则不登记属性监听",
    )
    _attribute_watch_handlers: list[Any] = PrivateAttr(default_factory=list)

    async def on_activate(self) -> None:
        await super().on_activate()
        _register_on_change_handlers(self)

    async def on_inactive(self) -> None:
        for h in self._attribute_watch_handlers:
            try:
                self._ctx._on_state_changed.remove(h)
            except ValueError:
                pass
        self._attribute_watch_handlers.clear()
        await super().on_inactive()

    async def fire(
        self,
        data: dict[str, Any] | EventContext | AttributeChangeEventData | None = None,
    ) -> None:
        """在交给基类前将属性变更载荷展开为与条件求值一致的 data。"""

        if isinstance(data, AttributeChangeEventData):
            data = data.model_copy(
                update={
                    "event_name": self.instance_name,
                    "data": data.as_payload(),
                }
            )
        await super().fire(data)


AttributeWatchEvent.registered_kind = "event"
event_registry.register("event", AttributeWatchEvent)
