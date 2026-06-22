from ff14_the_hunt.bear_tracker.enrich import build_hunt_record
from ff14_the_hunt.bear_tracker.resources import BearResources
from ff14_the_hunt.models import HuntQueryFilter


_RESOURCES = BearResources(
    {
        "DatabaseHunt": {
            "Sansheya": {
                "Patch": "DT",
                "Region": "Shaaloani",
                "Rank": 3,
                "RespawnTimer": [46.0, 2.0],
            },
        },
        "SpawnPoint": {},
        "DataCenters": {},
    },
)


def _row(**overrides) -> dict:
    row = {
        "huntKey": "Sansheya",
        "huntName": "Sansheya",
        "worldName": "Test",
        "isMaint": False,
        "lastDeathTime": 1_000_000.0,
    }
    row.update(overrides)
    return row


def test_open_window_without_last_mark_is_not_recently_spawned() -> None:
    record = build_hunt_record(
        timer_row=_row(),
        resources=_RESOURCES,
        query=HuntQueryFilter(),
        now=1_000_000.0 + 46 * 3600 + 60,
        recent_grace_seconds=900.0,
    )

    assert record is not None
    assert record.trigger_timer is not None
    assert record.recently_spawned is False


def test_recent_last_mark_is_recently_spawned() -> None:
    now = 1_000_000.0 + 46 * 3600 + 60
    record = build_hunt_record(
        timer_row=_row(lastMarkTime=now - 30),
        resources=_RESOURCES,
        query=HuntQueryFilter(),
        now=now,
        recent_grace_seconds=900.0,
    )

    assert record is not None
    assert record.recently_spawned is True
