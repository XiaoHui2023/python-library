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
    _original_callbacks: dict[str, Any] = PrivateAttr(default_factory=dict)

    @property
    def entity(self) -> Any:
        """触发后可引用的实际 entity 实例"""
        return self._entity_ref

    def _find_entities(self, hub: Hub) -> list:
        return [
            e for e in hub.entities.values()
            if e._type == self.entity_type
        ]

    async def on_validate(self, hub: Hub) -> None:
        if not self._find_entities(hub):
            raise ValueError(
                f"No entity of type {self.entity_type!r} found"
            )

    async def on_activate(self, hub: Hub) -> None:
        event_ref = self
        self._original_callbacks.clear()

        for entity in self._find_entities(hub):
            self._original_callbacks[entity.instance_name] = getattr(
                entity, self.callback, None
            )

            async def wrapper(_entity=entity, **kwargs):
                event_ref._entity_ref = _entity
                context = EventContext(
                    event_name=event_ref.instance_name,
                    data={"entity": _entity, **kwargs},
                )
                await event_ref.fire(context)

            setattr(entity, self.callback, wrapper)

    async def on_stop(self) -> None:
        for name, original in self._original_callbacks.items():
            entity = self._hub.entities.get(name)
            if entity is not None and original is not None:
                setattr(entity, self.callback, original)
        self._original_callbacks.clear()
        self._entity_ref = None