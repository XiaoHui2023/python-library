from ff14_the_hunt.models import HuntMarkRecord
from ff14_the_hunt.poll.spawn_dedup import SpawnReportTracker, spawn_cycle_key


def _mark(
    *,
    hunt_key: str = "Foo",
    world: str = "Bar",
    last_death: float = 1000.0,
    recently: bool = True,
) -> HuntMarkRecord:
    return HuntMarkRecord(
        hunt_key=hunt_key,
        hunt_name=hunt_key,
        world_name=world,
        last_death_time=last_death,
        recently_spawned=recently,
    )


def test_spawn_cycle_key_uses_last_death() -> None:
    mark = _mark(last_death=42.0)
    assert spawn_cycle_key(mark) == ("Foo", "Bar", 42.0)


def test_tracker_marks_first_recent_as_new() -> None:
    tracker = SpawnReportTracker()
    marks = [_mark()]
    tracker.apply(marks)
    assert marks[0].newly_spawned is True


def test_tracker_skips_repeat_within_same_cycle() -> None:
    tracker = SpawnReportTracker()
    first = [_mark()]
    tracker.apply(first)
    second = [_mark()]
    tracker.apply(second)
    assert second[0].newly_spawned is False
    assert second[0].recently_spawned is True


def test_tracker_reports_again_after_new_death_cycle() -> None:
    tracker = SpawnReportTracker()
    tracker.apply([_mark(last_death=10.0)])
    later = [_mark(last_death=20.0)]
    tracker.apply(later)
    assert later[0].newly_spawned is True


def test_tracker_clears_newly_when_not_recent() -> None:
    tracker = SpawnReportTracker()
    marks = [_mark(recently=False)]
    tracker.apply(marks)
    assert marks[0].newly_spawned is False
