from datetime import datetime, timedelta

from pydantic import Field

from .base import BaseScheduler


class At(BaseScheduler):
    hour: int = Field(0, ge=0, le=23, description="小时")
    minute: int = Field(0, ge=0, le=59, description="分钟")
    second: int = Field(0, ge=0, le=59, description="秒")
    weekday: int | None = Field(None, ge=0, le=6, description="星期几 (0=周一, 6=周日)")
    interval: int = Field(
        1,
        ge=1,
        description="未指定 weekday 时表示间隔天数；指定 weekday 时表示间隔周数",
    )

    def _with_schedule_time(self, dt: datetime) -> datetime:
        return dt.replace(
            hour=self.hour,
            minute=self.minute,
            second=self.second,
            microsecond=0,
        )

    def _next_target(self, reference: datetime) -> datetime:
        target = self._with_schedule_time(reference)

        if self.weekday is not None:
            days = (self.weekday - reference.weekday()) % 7
            target += timedelta(days=days)

            if target <= reference:
                target += timedelta(weeks=self.interval)

            return target

        if target <= reference:
            target += timedelta(days=self.interval)

        return target

    def _next_delay(self) -> float:
        now = datetime.now()
        reference = self._last_fire_at or now
        return max((self._next_target(reference) - now).total_seconds(), 0)

    def _condition(self) -> bool:
        now = datetime.now()
        last = self._last_fire_at
        if last is None:
            return False

        target = self._next_target(last)
        return last < target <= now