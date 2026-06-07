from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PollSleepSettings:
    """轮询休眠参数；供 ``compute_poll_sleep_seconds`` 与调度器共用。"""

    active_poll_interval_seconds: float = 600.0
    recent_poll_interval_seconds: float = 300.0
    fallback_poll_interval_seconds: float = 1800.0
    min_wakeup_seconds: float = 120.0

    def __post_init__(self) -> None:
        if self.active_poll_interval_seconds <= 0:
            raise ValueError("active_poll_interval_seconds must be > 0")
        if self.recent_poll_interval_seconds <= 0:
            raise ValueError("recent_poll_interval_seconds must be > 0")
        if self.fallback_poll_interval_seconds <= 0:
            raise ValueError("fallback_poll_interval_seconds must be > 0")
        if self.min_wakeup_seconds <= 0:
            raise ValueError("min_wakeup_seconds must be > 0")
