from ff14_the_hunt.bear_tracker.timer_theme import build_timer_display
from ff14_the_hunt.models import (
    HuntMarkRecord,
    SpawnWindowPhase,
    TimerBarColor,
    TimerKind,
)
from ff14_the_hunt.poll.sleep_plan import compute_poll_sleep_seconds
from ff14_the_hunt.poll.sleep_settings import PollSleepSettings
from ff14_the_hunt.poll.window_remaining import nearest_window_open_remaining_seconds

_SETTINGS = PollSleepSettings(
    active_poll_interval_seconds=600.0,
    recent_poll_interval_seconds=300.0,
    fallback_poll_interval_seconds=1800.0,
    min_wakeup_seconds=120.0,
)


def _mark(
    *,
    remaining: float | None = None,
    phase: SpawnWindowPhase = SpawnWindowPhase.ALMOST_OPEN,
    recently_spawned: bool = False,
) -> HuntMarkRecord:
    trigger = None
    if remaining is not None or phase != SpawnWindowPhase.ALMOST_OPEN:
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
    return HuntMarkRecord(
        hunt_key="k",
        hunt_name="n",
        world_name="w",
        trigger_timer=trigger,
        recently_spawned=recently_spawned,
    )


def test_nearest_window_open_picks_minimum() -> None:
    marks = [_mark(remaining=600.0), _mark(remaining=300.0)]
    assert nearest_window_open_remaining_seconds(marks) == 300.0


def test_nearest_window_open_ignores_open_phase() -> None:
    marks = [_mark(phase=SpawnWindowPhase.OPEN)]
    assert nearest_window_open_remaining_seconds(marks) is None


def test_wait_mode_sleeps_until_open_without_periodic_cap() -> None:
    now = 1_700_000_000.0
    marks = [_mark(remaining=72_000.0)]
    sleep = compute_poll_sleep_seconds(
        marks,
        settings=_SETTINGS,
        last_crawl_at=now,
        now=now,
    )
    assert sleep == 72_000.0


def test_wait_mode_clamps_small_remaining_to_min_wakeup() -> None:
    now = 1_700_000_000.0
    marks = [_mark(remaining=30.0)]
    sleep = compute_poll_sleep_seconds(
        marks,
        settings=_SETTINGS,
        last_crawl_at=now,
        now=now,
    )
    assert sleep == 120.0


def test_wait_mode_zero_when_open_elapsed() -> None:
    now = 1_700_000_900.0
    marks = [_mark(remaining=900.0)]
    sleep = compute_poll_sleep_seconds(
        marks,
        settings=_SETTINGS,
        last_crawl_at=now - 900.0,
        now=now,
    )
    assert sleep == 0.0


def test_active_mode_uses_active_interval() -> None:
    now = 1_700_000_000.0
    marks = [_mark(phase=SpawnWindowPhase.OPEN)]
    sleep = compute_poll_sleep_seconds(
        marks,
        settings=_SETTINGS,
        last_crawl_at=now - 200.0,
        now=now,
    )
    assert sleep == 400.0


def test_active_mode_uses_recent_interval_when_spawned() -> None:
    now = 1_700_000_000.0
    marks = [_mark(remaining=3600.0, recently_spawned=True)]
    sleep = compute_poll_sleep_seconds(
        marks,
        settings=_SETTINGS,
        last_crawl_at=now - 100.0,
        now=now,
    )
    assert sleep == 200.0


def test_fallback_mode_when_no_trigger() -> None:
    now = 1_700_000_000.0
    marks = [HuntMarkRecord(hunt_key="k", hunt_name="n", world_name="w")]
    sleep = compute_poll_sleep_seconds(
        marks,
        settings=_SETTINGS,
        last_crawl_at=now - 600.0,
        now=now,
    )
    assert sleep == 1200.0


def test_nearest_window_open_elapsed_since_crawl() -> None:
    marks = [_mark(remaining=900.0)]
    remaining = nearest_window_open_remaining_seconds(
        marks,
        last_crawl_at=1_700_000_000.0,
        now=1_700_000_600.0,
    )
    assert remaining == 300.0
