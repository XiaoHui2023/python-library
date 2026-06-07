from ff14_the_hunt.bear_tracker.spawn_window import (
    SpawnWindowPhase,
    compute_trigger_timer,
)


def test_trigger_window_open() -> None:
    last_death = 1_000_000.0
    timer = compute_trigger_timer(
        respawn_hours=(1.0, 2.0),
        last_death_time=last_death,
        now=last_death + 3600 + 60,
    )
    assert timer.phase == SpawnWindowPhase.OPEN
    assert timer.progress_percent is not None
    assert timer.progress_percent > 0
