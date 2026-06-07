from __future__ import annotations

import time

from ff14_the_hunt.bear_tracker.timer_theme import build_timer_display
from ff14_the_hunt.models import (
    SpawnWindowPhase,
    TimerBarColor,
    TimerDisplay,
    TimerKind,
)


def _format_duration(seconds: float) -> str:
    total = max(0, int(seconds))
    hours = total // 3600
    minutes = (total % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"


def compute_trigger_timer(
    *,
    respawn_hours: tuple[float, float],
    last_death_time: float,
    last_mark_time: float | None = None,
    missing_counter: float = 0.0,
    now: float | None = None,
) -> TimerDisplay:
    """复刻站点主计时列（组件 ``io``）的触发时间窗逻辑。

    Args:
        respawn_hours: ``(开窗延迟小时, 窗宽小时)``，来自 RespawnTimer 或 MaintTimer。
        last_death_time: 上次死亡 Unix 秒。
        last_mark_time: 有人标记发现时的时间；会收窄/平移开窗区间。
        missing_counter: 与站点一致的失踪计数加权。
        now: 当前 Unix 秒，默认 ``time.time()``。
    """
    if now is None:
        now = time.time()
    start_hours, window_hours = respawn_hours
    now_ms = now * 1000.0
    death_ms = last_death_time * 1000.0

    if last_mark_time is not None and last_mark_time > 0:
        mark_ms = last_mark_time * 1000.0
        open_ms = (missing_counter + 1.0) * start_hours * 3_600_000.0 + death_ms
        close_ms = window_hours * 3_600_000.0 + start_hours * 3_600_000.0 + mark_ms
    else:
        open_ms = start_hours * 3_600_000.0 + death_ms
        close_ms = open_ms + window_hours * 3_600_000.0

    if now_ms < open_ms:
        remaining = (open_ms - now_ms) / 1000.0
        return build_timer_display(
            kind=TimerKind.TRIGGER,
            phase=SpawnWindowPhase.ALMOST_OPEN,
            bar_color=TimerBarColor.ERROR,
            counts_up=False,
            remaining_seconds=remaining,
            summary=f"距离开窗 {_format_duration(remaining)}",
        )

    if now_ms < close_ms:
        elapsed = (now_ms - open_ms) / 1000.0
        span = (close_ms - open_ms) / 1000.0
        progress = (elapsed / span * 100.0) if span > 0 else 0.0
        return build_timer_display(
            kind=TimerKind.TRIGGER,
            phase=SpawnWindowPhase.OPEN,
            bar_color=TimerBarColor.SUCCESS,
            counts_up=True,
            elapsed_seconds=elapsed,
            progress_percent=min(progress, 999.0),
            summary=f"已开窗 {_format_duration(elapsed)}（{progress:.0f}%）",
        )

    elapsed_since_cap = (now_ms - close_ms) / 1000.0
    return build_timer_display(
        kind=TimerKind.TRIGGER,
        phase=SpawnWindowPhase.CAPPED,
        bar_color=TimerBarColor.INFO,
        counts_up=True,
        elapsed_seconds=elapsed_since_cap,
        summary=f"已强制（cap） {_format_duration(elapsed_since_cap)}",
    )


def is_window_open(timer: TimerDisplay | None) -> bool:
    return timer is not None and timer.phase == SpawnWindowPhase.OPEN


def is_recently_in_window(
    timer: TimerDisplay | None,
    *,
    grace_seconds: float = 900.0,
) -> bool:
    if timer is None or timer.phase != SpawnWindowPhase.OPEN:
        return False
    if timer.elapsed_seconds is None:
        return False
    return timer.elapsed_seconds <= grace_seconds
