from unittest.mock import MagicMock

from ff14_the_hunt import HuntPollScheduler, HuntQueryFilter, HuntRankKind
from ff14_the_hunt.bear_tracker.timer_theme import build_timer_display
from ff14_the_hunt.models import (
    HuntMarkRecord,
    SpawnWindowPhase,
    TimerBarColor,
    TimerKind,
)


def test_scheduler_resets_wait_after_fetch() -> None:
    hunt = MagicMock()
    mark = HuntMarkRecord(
        hunt_key="k",
        hunt_name="n",
        world_name="w",
        trigger_timer=build_timer_display(
            kind=TimerKind.TRIGGER,
            phase=SpawnWindowPhase.ALMOST_OPEN,
            bar_color=TimerBarColor.ERROR,
            counts_up=False,
            remaining_seconds=900.0,
            summary="test",
        ),
    )
    hunt.query_marks.return_value = [mark]

    scheduler = HuntPollScheduler(
        hunt,
        HuntQueryFilter(rank_kinds=[HuntRankKind.S]),
        poll_interval_seconds=1800.0,
        min_wakeup_seconds=120.0,
    )

    t0 = 1_700_000_000.0
    scheduler._last_marks = [mark]
    scheduler._last_crawl_at = t0
    wait_after_first = scheduler.seconds_until_next_fetch(now=t0)
    assert wait_after_first == 900.0

    wait_after_periodic = scheduler.seconds_until_next_fetch(now=t0 + 600.0)
    assert wait_after_periodic == 300.0

    scheduler._last_crawl_at = t0 + 600.0
    wait_after_reset = scheduler.seconds_until_next_fetch(now=t0 + 600.0)
    assert wait_after_reset == 900.0

    scheduler.fetch()
    assert hunt.query_marks.call_count == 1
