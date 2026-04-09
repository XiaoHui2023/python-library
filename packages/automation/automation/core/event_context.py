from pydantic import BaseModel, Field
from typing import Any

class EventContext(BaseModel):
    """事件触发时的上下文，在 trigger 管线中流转"""
    event_name: str
    data: dict[str, Any] = Field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)