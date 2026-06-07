from __future__ import annotations

from ff14_the_hunt.locale.names import translate_hunt_name, translate_region
from ff14_the_hunt.locale.tag import HuntDisplayLocale
from ff14_the_hunt.locale.spawn_map_display import (
    region_map_to_display_dict,
    spawn_layout_to_display_dict,
)
from ff14_the_hunt.models import (
    HuntCrawlPacket,
    HuntMarkRecord,
    HuntQueryFilter,
    HuntRankKind,
    SpawnWindowPhase,
    TimerDisplay,
    TimerKind,
)

PATCH_CODE_TO_EN: dict[str, str] = {
    "ARR": "A Realm Reborn",
    "HW": "Heavensward",
    "ShB": "Shadowbringers",
    "EW": "Endwalker",
    "DT": "Dawntrail",
}

RANK_KIND_TO_EN: dict[HuntRankKind, str] = {
    HuntRankKind.A: "A Rank",
    HuntRankKind.S: "S Rank",
    HuntRankKind.FATE: "FATE",
}

TIMER_KIND_TO_EN: dict[TimerKind, str] = {
    TimerKind.TRIGGER: "Trigger",
    TimerKind.CONDITION: "Condition",
    TimerKind.FATE: "FATE",
}

PHASE_TO_EN: dict[SpawnWindowPhase, str] = {
    SpawnWindowPhase.CLOSED: "Closed",
    SpawnWindowPhase.ALMOST_OPEN: "Almost open",
    SpawnWindowPhase.OPEN: "Open",
    SpawnWindowPhase.CAPPED: "Capped",
}


def patch_code_to_label(code: str) -> str:
    return PATCH_CODE_TO_EN.get(code, code)


def query_to_display_dict(query: HuntQueryFilter) -> dict[str, object]:
    payload: dict[str, object] = {
        "data_centers": list(query.data_centers),
        "worlds": list(query.worlds),
        "rank_kinds": [RANK_KIND_TO_EN.get(kind, kind.value) for kind in query.rank_kinds],
    }
    if query.patches:
        payload["patches"] = [patch_code_to_label(code) for code in query.patches]
    if query.hunt_keys:
        payload["hunt_keys"] = list(query.hunt_keys)
    if query.regions:
        payload["regions"] = list(query.regions)
    payload["include_untimed_marks"] = query.include_untimed_marks
    return payload


def _timer_to_display_dict(timer: TimerDisplay | None) -> dict[str, object] | None:
    if timer is None:
        return None
    item: dict[str, object] = {
        "kind": TIMER_KIND_TO_EN.get(timer.kind, timer.kind.value),
        "summary": timer.summary,
        "bar_color": timer.bar_color.value,
        "hex_color": timer.hex_color,
        "counts_up": timer.counts_up,
    }
    if timer.phase is not None:
        item["phase"] = PHASE_TO_EN.get(timer.phase, timer.phase.value)
    if timer.elapsed_seconds is not None:
        item["elapsed_seconds"] = timer.elapsed_seconds
    if timer.remaining_seconds is not None:
        item["remaining_seconds"] = timer.remaining_seconds
    if timer.progress_percent is not None:
        item["progress_percent"] = timer.progress_percent
    return item


def mark_to_display_dict(
    mark: HuntMarkRecord,
    *,
    embed_region_map_data: bool = True,
    region_map_file_name: str | None = None,
) -> dict[str, object]:
    locale = HuntDisplayLocale.EN
    region = mark.region
    if isinstance(region, list):
        region_text = translate_region(region, locale)
    else:
        region_text = translate_region(region, locale)

    item: dict[str, object] = {
        "hunt_key": mark.hunt_key,
        "hunt_name": translate_hunt_name(mark.hunt_key, locale),
        "world_name": mark.world_name,
        "region": region_text,
        "patch": patch_code_to_label(mark.patch),
        "rank": mark.rank,
        "last_death_time": mark.last_death_time,
        "last_mark_time": mark.last_mark_time,
        "missing_counter": mark.missing_counter,
        "is_maintenance": mark.is_maintenance,
        "recently_spawned": mark.recently_spawned,
        "newly_spawned": mark.newly_spawned,
    }
    if mark.fate_last_seen is not None:
        item["fate_last_seen"] = mark.fate_last_seen
    if mark.fate_last_death is not None:
        item["fate_last_death"] = mark.fate_last_death

    trigger = _timer_to_display_dict(mark.trigger_timer)
    if trigger is not None:
        item["trigger_timer"] = trigger
    condition = _timer_to_display_dict(mark.condition_timer)
    if condition is not None:
        item["condition_timer"] = condition
    fate = _timer_to_display_dict(mark.fate_timer)
    if fate is not None:
        item["fate_timer"] = fate

    if mark.spawn_map_layout is not None:
        item["spawn_map_layout"] = spawn_layout_to_display_dict(mark.spawn_map_layout)
    if mark.spawn_points:
        item["spawn_points"] = [
            {
                "point_key": point.point_key,
                "map_x": point.x,
                "map_y": point.y,
                "pixel_x": point.pixel_x,
                "pixel_y": point.pixel_y,
                "grid_x": point.grid_x,
                "grid_y": point.grid_y,
                "active": point.active,
            }
            for point in mark.spawn_points
        ]
    if mark.region_map is not None:
        item["region_map"] = region_map_to_display_dict(
            mark.region_map,
            embed_data=embed_region_map_data,
            file_name=region_map_file_name,
        )
    return item


def crawl_packet_to_display_dict(
    packet: HuntCrawlPacket,
    *,
    recently_spawned: list[HuntMarkRecord] | None = None,
    embed_region_map_data: bool = True,
    region_map_file_names: dict[tuple[str, str], str] | None = None,
) -> dict[str, object]:
    file_names = region_map_file_names or {}

    def _mark_dict(mark: HuntMarkRecord) -> dict[str, object]:
        key = (mark.hunt_key, mark.world_name)
        return mark_to_display_dict(
            mark,
            embed_region_map_data=embed_region_map_data,
            region_map_file_name=file_names.get(key),
        )

    payload: dict[str, object] = {
        "query": query_to_display_dict(packet.query),
        "crawled_at": packet.crawled_at,
        "next_fetch_at": packet.next_fetch_at,
        "marks": [_mark_dict(mark) for mark in packet.marks],
    }
    if recently_spawned is not None:
        payload["recently_spawned"] = [_mark_dict(mark) for mark in recently_spawned]
    return payload
