from .job import Job
from datetime import datetime

class Every(Job):
    """间隔执行"""
    seconds: float = 0
    minutes: float = 0
    hours: float = 0

    @property
    def interval(self) -> float:
        "间隔时间，单位：秒"
        return self.seconds + self.minutes * 60 + self.hours * 3600

    def should_run(self) -> bool:
        if (datetime.now() - self._last_run).total_seconds() < self.interval:
            return False
        return super().should_run()