from datetime import datetime, timedelta

from pydantic import Field

from .base import BaseScheduler


class At(BaseScheduler):
    hour: int = Field(0, ge=0, le=23, description="小时")
    minute: int = Field(0, ge=0, le=59, description="分钟")
    second: int = Field(0, ge=0, le=59, description="秒")
    weekday: int | None = Field(None, ge=0, le=6, description="星期几 (0=周一, 6=周日)")

    def _next_target(self, now: datetime) -> datetime:
        target = now.replace(
            hour=self.hour,
            minute=self.minute,
            second=self.second,
            microsecond=0,
        )

        if self.weekday is None:
            if target <= now:
                target += timedelta(days=1)
            return target

        days = (self.weekday - now.weekday()) % 7
        if days == 0 and target <= now:
            days = 7

        return target + timedelta(days=days)

    def _next_delay(self) -> float:
        now = datetime.now()
        return max((self._next_target(now) - now).total_seconds(), 0)

    def _condition(self) -> bool:
        now = datetime.now()
        last = self._last_fire_at
        if last is None:
            return False

        target = self._next_target(last)
        return last < target <= now