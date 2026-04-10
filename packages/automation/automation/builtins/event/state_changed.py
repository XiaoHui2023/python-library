from __future__ import annotations
from typing import Any, ClassVar, TYPE_CHECKING

from pydantic import Field, PrivateAttr

from automation.core.event import Event
from automation.core.event_context import EventContext

if TYPE_CHECKING:
    from automation.hub import Hub


class StateChangedEvent(Event):
    _abstract: ClassVar[bool] = False
    _type: ClassVar[str] = "state_changed"

    entity_type: str | None = Field(default=None, description="过滤实体类型（可选）")
    entity_name: str | None = Field(default=None, description="过滤实体实例名（可选）")
    attribute: str | None = Field(default=None, description="过滤属性名（可选）")

    _entity_ref: Any = PrivateAttr(default=None)
    _handler: Any = PrivateAttr(default=None)

    @property
    def entity(self) -> Any:
        return self._entity_ref

    async def on_activate(self, hub: Hub) -> None:
        event_ref = self

        async def handler(entity, attr, old, new):
            if event_ref.entity_type and entity._type != event_ref.entity_type:
                return
            if event_ref.entity_name and entity.instance_name != event_ref.entity_name:
                return
            if event_ref.attribute and attr != event_ref.attribute:
                return
            event_ref._entity_ref = entity
            context = EventContext(
                event_name=event_ref.instance_name,
                data={
                    "entity": entity,
                    "attribute": attr,
                    "old": old,
                    "new": new,
                },
            )
            await event_ref.fire(context)

        self._handler = handler
        hub._on_state_changed.append(handler)

    async def on_stop(self) -> None:
        if self._handler and self._hub:
            try:
                self._hub._on_state_changed.remove(self._handler)
            except ValueError:
                pass