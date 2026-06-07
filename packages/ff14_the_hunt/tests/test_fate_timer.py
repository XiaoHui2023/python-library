from ff14_the_hunt.bear_tracker.fate_timer import compute_fate_timer
from ff14_the_hunt.models import TimerBarColor, TimerKind


def test_fate_timer_since_seen_is_green() -> None:
    seen = 1_000_000.0
    death = 999_000.0
    timer = compute_fate_timer(
        fate_last_seen=seen,
        fate_last_death=death,
        now=seen + 120,
    )
    assert timer is not None
    assert timer.kind == TimerKind.FATE
    assert timer.bar_color == TimerBarColor.SUCCESS
    assert timer.counts_up is True


def test_fate_timer_since_death_is_red() -> None:
    seen = 1_000_000.0
    death = 1_000_100.0
    timer = compute_fate_timer(
        fate_last_seen=seen,
        fate_last_death=death,
        now=death + 60,
    )
    assert timer is not None
    assert timer.bar_color == TimerBarColor.ERROR
    assert timer.counts_up is True
