from .job import Job
from datetime import datetime, timedelta

class AT(Job):
    """定时执行"""
    weekday: int | None = None   # 0=周一, 6=周日, None=不限
    hour: int = 0
    minute: int = 0
    second: int = 0

    @property
    def target(self) -> datetime:
        """本周期的目标时间点"""
        now = datetime.now()
        base = now.replace(hour=self.hour, minute=self.minute, second=self.second, microsecond=0)

        if self.weekday is not None:
            days_diff = self.weekday - now.weekday()
            base += timedelta(days=days_diff)

        return base

    def should_run(self) -> bool:
        now = datetime.now()
        target = self.target
        if now < target or self._last_run >= target:
            return False
        return super().should_run()