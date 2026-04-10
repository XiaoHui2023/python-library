from __future__ import annotations
from typing import Any, ClassVar, TYPE_CHECKING

from pydantic import Field, PrivateAttr

from automation.core.event import Event
from automation.core.event_context import EventContext

if TYPE_CHECKING:
    from automation.hub import Hub


class CallbackEvent(Event):
    _abstract: ClassVar[bool] = False
    _type: ClassVar[str] = "callback"

    entity_type: str = Field(description="实体类型名")
    callback: str = Field(description="实体上的回调属性名")

    _entity_ref: Any = PrivateAttr(default=None)
    _original_callback: Any = PrivateAttr(default=None)
    _wrapper: Any = PrivateAttr(default=None)

    @property
    def entity(self) -> Any:
        """触发后可引用的实际 entity 实例"""
        return self._entity_ref

    async def on_validate(self, hub: Hub) -> None:
        if self.entity_type not in hub.entities:
            raise ValueError(f"Entity {self.entity_type!r} not found")
        self._entity_ref = hub.entities[self.entity_type]

    async def on_activate(self, hub: Hub) -> None:
        entity = hub.entities[self.entity_type]
        self._entity_ref = entity
        self._original_callback = getattr(entity, self.callback, None)

        event_ref = self

        async def wrapper(**kwargs):
            context = EventContext(
                event_name=event_ref.instance_name,
                data=kwargs,
            )
            await event_ref.fire(context)

        self._wrapper = wrapper
        setattr(entity, self.callback, wrapper)

    async def on_stop(self) -> None:
        if self._entity_ref is not None and self._original_callback is not None:
            setattr(self._entity_ref, self.callback, self._original_callback)