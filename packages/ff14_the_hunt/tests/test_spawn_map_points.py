from ff14_the_hunt.models import MapCoordinate
from ff14_the_hunt.bear_tracker.spawn_points import list_map_coordinates
from ff14_the_hunt.spawn_map.points import select_display_spawn_points


def test_select_display_spawn_points_keeps_only_possible_points() -> None:
    points = [
        MapCoordinate(point_key="SpawnPoint01", x=0.1, y=0.2, active=False),
        MapCoordinate(point_key="SpawnPoint02", x=0.3, y=0.4, active=True),
    ]
    selected = select_display_spawn_points(points)
    assert len(selected) == 1
    assert selected[0].point_key == "SpawnPoint02"


def test_select_display_spawn_points_does_not_fallback_to_excluded_points() -> None:
    points = [
        MapCoordinate(point_key="SpawnPoint01", x=0.1, y=0.2, active=None),
        MapCoordinate(point_key="SpawnPoint02", x=0.3, y=0.4, active=False),
    ]
    selected = select_display_spawn_points(points)
    assert selected == []


def test_list_map_coordinates_marks_unreported_points_as_possible() -> None:
    points = list_map_coordinates(
        {
            "Dimensions": [41, 41],
            "DisplayPoints": 3,
            "SpawnPoint01": [1, 1],
            "SpawnPoint02": [2, 2],
            "SpawnPoint03": [3, 3],
        },
        api_states={
            "SpawnPoint01": {"State": True, "Verified": True},
            "SpawnPoint02": {"State": False, "Verified": True},
        },
    )

    assert [(point.point_key, point.active) for point in points] == [
        ("SpawnPoint01", False),
        ("SpawnPoint02", False),
        ("SpawnPoint03", True),
    ]
