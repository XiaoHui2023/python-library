from __future__ import annotations

from typing import Any

from ff14_the_hunt.bear_tracker.resources import BearResources
from ff14_the_hunt.bear_tracker.spawn_points import list_map_coordinates
from ff14_the_hunt.models import HuntMarkRecord

from ff14_the_hunt.spawn_map.coordinates import with_pixel_coordinates
from ff14_the_hunt.spawn_map.layout import layout_from_spawn_entry
from ff14_the_hunt.spawn_map.points import resolve_region_name, select_display_spawn_points
from ff14_the_hunt.spawn_map.region_fetch import RegionMapFetcher
from ff14_the_hunt.spawn_map.region_image import build_region_map_image


def _spawn_entry_for_record(
    record: HuntMarkRecord,
    resources: BearResources,
) -> dict[str, Any] | None:
    meta = resources.hunt_meta(record.hunt_key)
    map_key = resources.spawn_map_key(record.hunt_key, meta)
    if not map_key:
        return None
    return resources.spawn_point.get(map_key)


def populate_spawn_points(
    record: HuntMarkRecord,
    *,
    resources: BearResources,
    spawn_states: dict[str, Any] | None,
) -> None:
    """为刚刷新记录填充 ``spawn_points`` 与 ``spawn_map_layout``。"""
    if not record.recently_spawned:
        record.spawn_points = []
        record.spawn_map_layout = None
        record.region_map = None
        return
    spawn_entry = _spawn_entry_for_record(record, resources)
    record.spawn_map_layout = layout_from_spawn_entry(spawn_entry)
    raw_points = list_map_coordinates(spawn_entry, api_states=spawn_states)
    record.spawn_points = select_display_spawn_points(raw_points)


def attach_region_map(
    record: HuntMarkRecord,
    *,
    fetcher: RegionMapFetcher,
) -> None:
    """拉取站点区域原图，并补全刷点像素坐标。"""
    record.region_map = None
    if not record.recently_spawned or not record.spawn_points:
        return
    region = resolve_region_name(record.region)
    if not region:
        return
    region_map = build_region_map_image(region=region, fetcher=fetcher)
    if region_map is None:
        return
    record.region_map = region_map
    record.spawn_points = with_pixel_coordinates(
        record.spawn_points,
        image_width=region_map.width,
        image_height=region_map.height,
    )


def enrich_recent_spawn_details(
    records: list[HuntMarkRecord],
    timer_rows: list[dict[str, Any]],
    *,
    resources: BearResources,
    fetcher: RegionMapFetcher | None,
    load_spawn_states,
    include_region_map: bool,
) -> None:
    """为刚刷新记录补全刷点、布局参数与可选区域原图。"""
    row_index = {
        (str(row.get("huntKey") or ""), str(row.get("worldName") or "")): row
        for row in timer_rows
    }
    for record in records:
        if not record.recently_spawned:
            record.spawn_points = []
            record.spawn_map_layout = None
            record.region_map = None
            continue
        row = row_index.get((record.hunt_key, record.world_name))
        spawn_states = load_spawn_states(row, resources) if row is not None else None
        populate_spawn_points(
            record,
            resources=resources,
            spawn_states=spawn_states,
        )
        if include_region_map and fetcher is not None:
            attach_region_map(record, fetcher=fetcher)
