from __future__ import annotations

import time

from ff14_the_hunt.bear_tracker.spawn_window import _format_duration
from ff14_the_hunt.bear_tracker.timer_theme import build_timer_display
from ff14_the_hunt.models import (
    SpawnWindowPhase,
    TimerBarColor,
    TimerDisplay,
    TimerKind,
)


def compute_fate_timer(
    *,
    fate_last_seen: float | None,
    fate_last_death: float | None,
    now: float | None = None,
) -> TimerDisplay | None:
    """7.0 部分 S 猎 FATE 链计时（站点组件 ``lo`` 的 FATE 分支）。"""
    if fate_last_seen is None or fate_last_death is None:
        return None
    if now is None:
        now = time.time()
    now_ms = now * 1000.0
    seen_ms = fate_last_seen * 1000.0
    death_ms = fate_last_death * 1000.0

    if death_ms > seen_ms:
        delta = now_ms - death_ms
        return build_timer_display(
            kind=TimerKind.FATE,
            phase=SpawnWindowPhase.CLOSED,
            bar_color=TimerBarColor.ERROR,
            counts_up=True,
            elapsed_seconds=delta / 1000.0,
            summary=f"FATE 已结束 {_format_duration(delta / 1000.0)}",
        )

    delta = now_ms - seen_ms
    return build_timer_display(
        kind=TimerKind.FATE,
        phase=SpawnWindowPhase.OPEN,
        bar_color=TimerBarColor.SUCCESS,
        counts_up=True,
        elapsed_seconds=delta / 1000.0,
        summary=f"FATE 进行中 {_format_duration(delta / 1000.0)}",
    )


def compute_fate_condition_timer(
    *,
    last_death_time: float,
    fate_last_seen: float | None,
    fate_last_death: float | None,
    now: float | None = None,
) -> TimerDisplay | None:
    """兼容旧名；``last_death_time`` 未使用。"""
    del last_death_time
    return compute_fate_timer(
        fate_last_seen=fate_last_seen,
        fate_last_death=fate_last_death,
        now=now,
    )
