from __future__ import annotations

import time

from ff14_the_hunt.models import HuntMarkRecord

from ff14_the_hunt.poll.monitor_mode import (
    PollMonitorMode,
    any_recently_spawned,
    resolve_poll_monitor_mode,
)
from ff14_the_hunt.poll.sleep_settings import PollSleepSettings
from ff14_the_hunt.poll.window_remaining import nearest_window_open_remaining_seconds


def _interval_remaining(
    *,
    interval_seconds: float,
    last_crawl_at: float,
    now: float,
) -> float:
    elapsed = max(0.0, now - last_crawl_at)
    remaining = interval_seconds - elapsed
    if remaining <= 0:
        return 0.0
    return remaining


def _active_poll_interval_seconds(
    marks: list[HuntMarkRecord],
    settings: PollSleepSettings,
) -> float:
    if any_recently_spawned(marks):
        return settings.recent_poll_interval_seconds
    return settings.active_poll_interval_seconds


def compute_poll_sleep_seconds(
    marks: list[HuntMarkRecord],
    *,
    settings: PollSleepSettings,
    last_crawl_at: float,
    now: float | None = None,
) -> float:
    """按轮询模式计算距下次爬取应等待的秒数。

    Args:
        marks: 上一次爬取得到的记录。
        settings: 各模式下的间隔与开窗唤醒下限。
        last_crawl_at: 上次爬取完成的 Unix 秒。
        now: 当前 Unix 秒，默认 ``time.time()``。

    Returns:
        建议休眠秒数；``0`` 表示应立即爬取。
    """
    if now is None:
        now = time.time()

    mode = resolve_poll_monitor_mode(marks)
    if mode == PollMonitorMode.ACTIVE:
        interval = _active_poll_interval_seconds(marks, settings)
        return _interval_remaining(
            interval_seconds=interval,
            last_crawl_at=last_crawl_at,
            now=now,
        )

    if mode == PollMonitorMode.WAIT_UNTIL_OPEN:
        open_remaining = nearest_window_open_remaining_seconds(
            marks,
            last_crawl_at=last_crawl_at,
            now=now,
        )
        if open_remaining is None:
            return _interval_remaining(
                interval_seconds=settings.fallback_poll_interval_seconds,
                last_crawl_at=last_crawl_at,
                now=now,
            )
        if open_remaining <= 0:
            return 0.0
        return max(settings.min_wakeup_seconds, open_remaining)

    return _interval_remaining(
        interval_seconds=settings.fallback_poll_interval_seconds,
        last_crawl_at=last_crawl_at,
        now=now,
    )
