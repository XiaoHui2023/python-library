from unittest.mock import patch

from ff14_the_hunt import FF14TheHunt, HuntQueryFilter, HuntRankKind
from ff14_the_hunt.bear_tracker.enrich import mark_has_display_timer
from ff14_the_hunt.bear_tracker.resources import BearResources
from ff14_the_hunt.bear_tracker.timer_theme import build_timer_display
from ff14_the_hunt.models import (
    HuntMarkRecord,
    SpawnWindowPhase,
    TimerBarColor,
    TimerKind,
)

_MOCK_RESOURCES = BearResources(
    {
        "DatabaseHunt": {
            "Arch Aethereater Kozama'uka": {
                "Patch": "DT",
                "Region": "Kozama'uka",
                "Rank": 5,
            },
            "Sansheya": {
                "Patch": "DT",
                "Region": "Shaaloani",
                "Rank": 3,
                "RespawnTimer": [46.0, 2.0],
            },
        },
        "SpawnPoint": {},
        "DataCenters": {"猫小胖": {"Region": "CN", "Names": ["静语庄园"]}},
    },
)

_TIMER_ROWS = [
    {
        "huntKey": "Arch Aethereater Kozama'uka",
        "huntName": "Arch Aethereater Kozama'uka",
        "worldName": "静语庄园",
        "isMaint": True,
        "lastDeathTime": 1_780_383_300.0,
    },
    {
        "huntKey": "Sansheya",
        "huntName": "Sansheya",
        "worldName": "静语庄园",
        "isMaint": False,
        "lastDeathTime": 1_780_800_000.0,
        "fateLastSeen": 1_780_830_000.0,
    },
]


def _trigger_record(*, hunt_key: str) -> HuntMarkRecord:
    return HuntMarkRecord(
        hunt_key=hunt_key,
        hunt_name=hunt_key,
        world_name="静语庄园",
        trigger_timer=build_timer_display(
            kind=TimerKind.TRIGGER,
            phase=SpawnWindowPhase.ALMOST_OPEN,
            bar_color=TimerBarColor.ERROR,
            counts_up=False,
            remaining_seconds=60.0,
            summary="test",
        ),
    )


def test_mark_has_display_timer() -> None:
    untimed = HuntMarkRecord(hunt_key="a", hunt_name="a", world_name="w")
    assert mark_has_display_timer(untimed) is False
    assert mark_has_display_timer(_trigger_record(hunt_key="b")) is True


def test_query_filter_defaults_exclude_untimed() -> None:
    assert HuntQueryFilter().include_untimed_marks is False


def test_query_marks_excludes_untimed_by_default() -> None:
    hunt = FF14TheHunt(
        worlds=["静语庄园"],
        rank_kinds=[HuntRankKind.S],
        patches=["DT"],
    )
    with patch.object(hunt, "ensure_resources", return_value=_MOCK_RESOURCES):
        with patch.object(
            hunt._client,
            "last_death_timers",
            return_value=list(_TIMER_ROWS),
        ):
            marks = hunt.query_marks()
    assert [mark.hunt_key for mark in marks] == ["Sansheya"]


def test_query_marks_includes_untimed_when_enabled() -> None:
    hunt = FF14TheHunt(
        worlds=["静语庄园"],
        rank_kinds=[HuntRankKind.S],
        patches=["DT"],
        include_untimed_marks=True,
    )
    with patch.object(hunt, "ensure_resources", return_value=_MOCK_RESOURCES):
        with patch.object(
            hunt._client,
            "last_death_timers",
            return_value=list(_TIMER_ROWS),
        ):
            marks = hunt.query_marks()
    assert len(marks) == 2


def test_ff14_the_hunt_constructor_forwards_include_untimed_marks() -> None:
    hunt = FF14TheHunt(
        worlds=["静语庄园"],
        include_untimed_marks=True,
    )
    assert hunt.query.include_untimed_marks is True
