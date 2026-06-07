from ff14_the_hunt.models import MapCoordinate
from ff14_the_hunt.spawn_map.points import select_display_spawn_points


def test_select_display_spawn_points_prefers_active() -> None:
    points = [
        MapCoordinate(point_key="SpawnPoint01", x=0.1, y=0.2, active=False),
        MapCoordinate(point_key="SpawnPoint02", x=0.3, y=0.4, active=True),
    ]
    selected = select_display_spawn_points(points)
    assert len(selected) == 1
    assert selected[0].point_key == "SpawnPoint02"


def test_select_display_spawn_points_keeps_all_when_no_active() -> None:
    points = [
        MapCoordinate(point_key="SpawnPoint01", x=0.1, y=0.2, active=None),
        MapCoordinate(point_key="SpawnPoint02", x=0.3, y=0.4, active=False),
    ]
    selected = select_display_spawn_points(points)
    assert len(selected) == 2
