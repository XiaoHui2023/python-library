from __future__ import annotations

import time

from ff14_the_hunt.models import SpawnWindowPhase, TimerDisplay

from ff14_the_hunt.bear_tracker.spawn_window import _format_duration


def compute_fate_condition_timer(
    *,
    last_death_time: float,
    fate_last_seen: float | None,
    fate_last_death: float | None,
    now: float | None = None,
) -> TimerDisplay | None:
    """7.0 部分 S 猎（如 Arch Aethereater）使用的 FATE 链条件计时（组件 ``lo`` 前半）。"""
    if fate_last_seen is None or fate_last_death is None:
        return None
    if now is None:
        now = time.time()
    now_ms = now * 1000.0
    seen_ms = fate_last_seen * 1000.0
    death_ms = fate_last_death * 1000.0

    if death_ms > seen_ms:
        delta = now_ms - death_ms
        return TimerDisplay(
            label="condition",
            phase=SpawnWindowPhase.CLOSED,
            elapsed_seconds=delta / 1000.0,
            summary=f"FATE 已结束 {_format_duration(delta / 1000.0)}",
        )

    delta = now_ms - seen_ms
    return TimerDisplay(
        label="condition",
        phase=SpawnWindowPhase.OPEN,
        elapsed_seconds=delta / 1000.0,
        summary=f"FATE 进行中 {_format_duration(delta / 1000.0)}",
    )
