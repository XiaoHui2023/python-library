from datetime import datetime

from pydantic import Field, model_validator

from .base import BaseScheduler


class Every(BaseScheduler):
    seconds: float = Field(0, ge=0, description="秒")
    minutes: float = Field(0, ge=0, description="分钟")
    hours: float = Field(0, ge=0, description="小时")
    days: float = Field(0, ge=0, description="天")

    @model_validator(mode="after")
    def _validate_period(self):
        if self.period <= 0:
            raise ValueError("Every period must be greater than 0")
        return self

    @property
    def period(self) -> float:
        return (
            self.seconds
            + self.minutes * 60
            + self.hours * 3600
            + self.days * 86400
        )

    def _next_delay(self) -> float:
        if self._last_fire_at is None:
            return 0
        elapsed = (datetime.now() - self._last_fire_at).total_seconds()
        return max(self.period - elapsed, 0)

    def _condition(self) -> bool:
        if self._last_fire_at is None:
            return False
        return (datetime.now() - self._last_fire_at).total_seconds() >= self.period