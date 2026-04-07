from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from .base import ScheduledEvent
from scheduler import At


class AtEvent(ScheduledEvent):
    _type: ClassVar[str] = "at"

    weekday: int | None = Field(default=None, ge=0, le=6)
    hour: int = Field(default=0, ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)
    second: int = Field(default=0, ge=0, le=59)
    max_runs: int | None = Field(default=None, ge=1)

    def _create_job(self) -> At:
        return At(
            weekday=self.weekday,
            hour=self.hour,
            minute=self.minute,
            second=self.second,
            max_runs=self.max_runs,
        )