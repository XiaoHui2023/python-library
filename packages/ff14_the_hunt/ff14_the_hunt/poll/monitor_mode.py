from __future__ import annotations

from enum import Enum

from ff14_the_hunt.models import HuntMarkRecord, SpawnWindowPhase


class PollMonitorMode(str, Enum):
    """上次爬取结果对应的轮询节奏模式。"""

    ACTIVE = "active"
    WAIT_UNTIL_OPEN = "wait_until_open"
    FALLBACK = "fallback"


def mark_needs_active_poll(mark: HuntMarkRecord) -> bool:
    """单条记录是否应使用开窗/强制期/刚刷新等短间隔轮询。"""
    if mark.recently_spawned:
        return True
    trigger = mark.trigger_timer
    if trigger is not None and trigger.phase in (
        SpawnWindowPhase.OPEN,
        SpawnWindowPhase.CAPPED,
    ):
        return True
    fate = mark.fate_timer
    if fate is not None and fate.phase == SpawnWindowPhase.OPEN:
        return True
    return False


def mark_has_almost_open_trigger(mark: HuntMarkRecord) -> bool:
    """单条记录是否处于「即将开窗」触发倒计时。"""
    trigger = mark.trigger_timer
    if trigger is None:
        return False
    return trigger.phase == SpawnWindowPhase.ALMOST_OPEN


def resolve_poll_monitor_mode(marks: list[HuntMarkRecord]) -> PollMonitorMode:
    """根据上次爬取记录选择轮询模式。

    Args:
        marks: 上次爬取得到的狩猎记录。

    Returns:
        ``ACTIVE``：存在开窗中、强制期、刚刷新或 FATE 进行中。
        ``WAIT_UNTIL_OPEN``：全部为即将开窗且无活跃项。
        ``FALLBACK``：无可用触发计时（占位行等）。
    """
    if not marks:
        return PollMonitorMode.FALLBACK

    if any(mark_needs_active_poll(mark) for mark in marks):
        return PollMonitorMode.ACTIVE

    if any(mark_has_almost_open_trigger(mark) for mark in marks):
        return PollMonitorMode.WAIT_UNTIL_OPEN

    return PollMonitorMode.FALLBACK


def any_recently_spawned(marks: list[HuntMarkRecord]) -> bool:
    """记录中是否存在刚刷新条目。"""
    return any(mark.recently_spawned for mark in marks)
