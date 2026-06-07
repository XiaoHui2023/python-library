from ff14_the_hunt.bear_tracker.timer_theme import build_timer_display
from ff14_the_hunt.models import (
    HuntMarkRecord,
    SpawnWindowPhase,
    TimerBarColor,
    TimerKind,
)
from ff14_the_hunt.poll.monitor_mode import (
    PollMonitorMode,
    mark_needs_active_poll,
    resolve_poll_monitor_mode,
)


def _mark(
    *,
    phase: SpawnWindowPhase | None = None,
    remaining: float | None = None,
    recently_spawned: bool = False,
    fate_phase: SpawnWindowPhase | None = None,
) -> HuntMarkRecord:
    trigger = None
    if phase is not None:
        kwargs: dict = {
            "kind": TimerKind.TRIGGER,
            "phase": phase,
            "bar_color": TimerBarColor.ERROR,
            "counts_up": phase != SpawnWindowPhase.ALMOST_OPEN,
            "summary": "test",
        }
        if remaining is not None:
            kwargs["remaining_seconds"] = remaining
        if phase == SpawnWindowPhase.OPEN:
            kwargs["bar_color"] = TimerBarColor.SUCCESS
            kwargs["elapsed_seconds"] = 60.0
        trigger = build_timer_display(**kwargs)

    fate = None
    if fate_phase is not None:
        fate = build_timer_display(
            kind=TimerKind.FATE,
            phase=fate_phase,
            bar_color=TimerBarColor.SUCCESS,
            counts_up=True,
            elapsed_seconds=30.0,
            summary="fate",
        )

    return HuntMarkRecord(
        hunt_key="k",
        hunt_name="n",
        world_name="w",
        trigger_timer=trigger,
        fate_timer=fate,
        recently_spawned=recently_spawned,
    )


def test_resolve_wait_when_all_almost_open() -> None:
    marks = [
        _mark(phase=SpawnWindowPhase.ALMOST_OPEN, remaining=3600.0),
        _mark(phase=SpawnWindowPhase.ALMOST_OPEN, remaining=7200.0),
    ]
    assert resolve_poll_monitor_mode(marks) == PollMonitorMode.WAIT_UNTIL_OPEN


def test_resolve_active_when_window_open() -> None:
    marks = [_mark(phase=SpawnWindowPhase.OPEN)]
    assert resolve_poll_monitor_mode(marks) == PollMonitorMode.ACTIVE


def test_resolve_active_when_capped() -> None:
    marks = [_mark(phase=SpawnWindowPhase.CAPPED)]
    assert resolve_poll_monitor_mode(marks) == PollMonitorMode.ACTIVE


def test_resolve_active_when_recently_spawned() -> None:
    marks = [_mark(phase=SpawnWindowPhase.ALMOST_OPEN, recently_spawned=True)]
    assert resolve_poll_monitor_mode(marks) == PollMonitorMode.ACTIVE


def test_resolve_active_when_fate_open() -> None:
    marks = [_mark(fate_phase=SpawnWindowPhase.OPEN)]
    assert resolve_poll_monitor_mode(marks) == PollMonitorMode.ACTIVE


def test_resolve_fallback_when_no_timer() -> None:
    marks = [HuntMarkRecord(hunt_key="k", hunt_name="n", world_name="w")]
    assert resolve_poll_monitor_mode(marks) == PollMonitorMode.FALLBACK


def test_mark_needs_active_poll_open_beats_almost_open() -> None:
    assert mark_needs_active_poll(_mark(phase=SpawnWindowPhase.OPEN)) is True
    assert mark_needs_active_poll(_mark(phase=SpawnWindowPhase.ALMOST_OPEN)) is False
