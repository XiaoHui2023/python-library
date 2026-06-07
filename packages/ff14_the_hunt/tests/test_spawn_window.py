from ff14_the_hunt.bear_tracker.spawn_window import (
    SpawnWindowPhase,
    compute_trigger_timer,
)
from ff14_the_hunt.models import TimerBarColor, TimerKind


def test_trigger_window_open() -> None:
    last_death = 1_000_000.0
    timer = compute_trigger_timer(
        respawn_hours=(1.0, 2.0),
        last_death_time=last_death,
        now=last_death + 3600 + 60,
    )
    assert timer.kind == TimerKind.TRIGGER
    assert timer.phase == SpawnWindowPhase.OPEN
    assert timer.bar_color == TimerBarColor.SUCCESS
    assert timer.hex_color == "#01b574"
    assert timer.counts_up is True
    assert timer.progress_percent is not None
    assert timer.progress_percent > 0


def test_trigger_window_closed_is_red_countdown() -> None:
    last_death = 1_000_000.0
    timer = compute_trigger_timer(
        respawn_hours=(2.0, 3.0),
        last_death_time=last_death,
        now=last_death + 1800,
    )
    assert timer.phase == SpawnWindowPhase.ALMOST_OPEN
    assert timer.bar_color == TimerBarColor.ERROR
    assert timer.counts_up is False
    assert timer.remaining_seconds is not None
    assert timer.remaining_seconds > 0


def test_trigger_window_capped_is_blue() -> None:
    last_death = 1_000_000.0
    timer = compute_trigger_timer(
        respawn_hours=(1.0, 2.0),
        last_death_time=last_death,
        now=last_death + 4 * 3600,
    )
    assert timer.phase == SpawnWindowPhase.CAPPED
    assert timer.bar_color == TimerBarColor.INFO
    assert timer.hex_color == "#0075ff"
    assert timer.counts_up is True
