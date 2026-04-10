from __future__ import annotations
from typing import ClassVar

from pydantic import Field

from ._scheduled import ScheduledEvent
from scheduler import Every

class EveryEvent(ScheduledEvent):
    _type: ClassVar[str] = "every"

    seconds: float = Field(default=0, ge=0)
    minutes: float = Field(default=0, ge=0)
    hours: float = Field(default=0, ge=0)
    days: float = Field(default=0, ge=0)
    immediate: bool = Field(default=False)
    max_runs: int | None = Field(default=None, ge=1)

    async def on_validate(self, hub) -> None:
        total = self.seconds + self.minutes * 60 + self.hours * 3600 + self.days * 86400
        if total <= 0:
            raise ValueError("EveryEvent requires at least one interval > 0")

    def _create_job(self) -> Every:
        return Every(
            seconds=self.seconds,
            minutes=self.minutes,
            hours=self.hours,
            days=self.days,
            immediate=self.immediate,
            max_runs=self.max_runs,
        )