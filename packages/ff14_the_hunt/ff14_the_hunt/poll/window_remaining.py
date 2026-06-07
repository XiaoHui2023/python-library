from __future__ import annotations

from ff14_the_hunt.models import HuntMarkRecord, SpawnWindowPhase

from ff14_the_hunt.poll.monitor_mode import mark_has_almost_open_trigger


def nearest_window_open_remaining_seconds(
    marks: list[HuntMarkRecord],
    *,
    last_crawl_at: float | None = None,
    now: float | None = None,
) -> float | None:
    """取最短「距离开窗」剩余秒数。

    Args:
        marks: 上次爬取得到的记录。
        last_crawl_at: 上次爬取 Unix 秒；与 ``now`` 同时给出时扣减其间流逝时间。
        now: 当前 Unix 秒。

    Returns:
        有「即将开窗」候选时返回最短剩余秒数；否则 ``None``。
    """
    candidates: list[float] = []
    for mark in marks:
        if not mark_has_almost_open_trigger(mark):
            continue
        timer = mark.trigger_timer
        if timer is None or timer.remaining_seconds is None:
            continue
        remaining = float(timer.remaining_seconds)
        if remaining > 0:
            candidates.append(remaining)
    if not candidates:
        return None

    remaining = min(candidates)
    if last_crawl_at is not None and now is not None:
        elapsed = max(0.0, now - last_crawl_at)
        remaining = max(0.0, remaining - elapsed)
        if remaining <= 0:
            return 0.0
    return remaining


def nearest_trigger_remaining_seconds(
    marks: list[HuntMarkRecord],
    *,
    last_crawl_at: float | None = None,
    now: float | None = None,
) -> float | None:
    """``nearest_window_open_remaining_seconds`` 的兼容别名。"""
    return nearest_window_open_remaining_seconds(
        marks,
        last_crawl_at=last_crawl_at,
        now=now,
    )
