from __future__ import annotations

import time
from typing import Any

from ff14_the_hunt.models import HuntMarkRecord, HuntQueryFilter, TimerDisplay

from ff14_the_hunt.bear_tracker.fate_timer import compute_fate_condition_timer
from ff14_the_hunt.bear_tracker.resources import BearResources
from ff14_the_hunt.bear_tracker.spawn_points import list_map_coordinates
from ff14_the_hunt.bear_tracker.spawn_window import (
    compute_trigger_timer,
    is_recently_in_window,
)


def _passes_filter(
    *,
    hunt_key: str,
    meta: dict[str, Any],
    world_name: str,
    query: HuntQueryFilter,
) -> bool:
    if query.hunt_keys and hunt_key not in query.hunt_keys:
        return False
    patch = str(meta.get("Patch", ""))
    if query.patches and patch not in query.patches:
        return False
    region = meta.get("Region", "")
    if query.regions:
        region_text = region if isinstance(region, str) else " ".join(region)
        if not any(item in region_text for item in query.regions):
            return False
    if query.worlds and world_name not in query.worlds:
        return False
    return True


def build_hunt_record(
    *,
    timer_row: dict[str, Any],
    resources: BearResources,
    spawn_states: dict[str, Any] | None,
    query: HuntQueryFilter,
    now: float | None = None,
    recent_grace_seconds: float = 900.0,
) -> HuntMarkRecord | None:
    hunt_key = str(timer_row.get("huntKey") or timer_row.get("huntName") or "")
    world_name = str(timer_row.get("worldName") or "")
    if not hunt_key or not world_name:
        return None

    meta = resources.hunt_meta(hunt_key)
    if not _passes_filter(
        hunt_key=hunt_key,
        meta=meta,
        world_name=world_name,
        query=query,
    ):
        return None

    is_maint = bool(timer_row.get("isMaint"))
    timer_pair = meta.get("MaintTimer") if is_maint else meta.get("RespawnTimer")
    last_death = timer_row.get("lastDeathTime")
    last_mark = timer_row.get("lastMarkTime")
    missing = float(timer_row.get("missingCounter") or 0.0)

    trigger: TimerDisplay | None = None
    if isinstance(timer_pair, (list, tuple)) and len(timer_pair) >= 2 and last_death:
        trigger = compute_trigger_timer(
            respawn_hours=(float(timer_pair[0]), float(timer_pair[1])),
            last_death_time=float(last_death),
            last_mark_time=float(last_mark) if last_mark else None,
            missing_counter=missing,
            now=now,
        )

    condition = compute_fate_condition_timer(
        last_death_time=float(last_death or 0.0),
        fate_last_seen=timer_row.get("fateLastSeen"),
        fate_last_death=timer_row.get("fateLastDeath"),
        now=now,
    )

    map_key = resources.spawn_map_key(hunt_key, meta)
    spawn_entry = resources.spawn_point.get(map_key) if map_key else None
    points = list_map_coordinates(spawn_entry, api_states=spawn_states)

    recently = is_recently_in_window(trigger, grace_seconds=recent_grace_seconds)
    if last_mark and now is not None:
        if now - float(last_mark) <= recent_grace_seconds:
            recently = True
    elif last_mark:
        if time.time() - float(last_mark) <= recent_grace_seconds:
            recently = True

    region = meta.get("Region", "")
    return HuntMarkRecord(
        hunt_key=hunt_key,
        hunt_name=str(timer_row.get("huntName") or hunt_key),
        world_name=world_name,
        region=region,
        patch=str(meta.get("Patch", "")),
        rank=meta.get("Rank"),
        last_death_time=float(last_death) if last_death else None,
        last_mark_time=float(last_mark) if last_mark else None,
        missing_counter=missing,
        is_maintenance=is_maint,
        fate_last_seen=timer_row.get("fateLastSeen"),
        fate_last_death=timer_row.get("fateLastDeath"),
        trigger_timer=trigger,
        condition_timer=condition,
        spawn_points=points,
        recently_spawned=recently,
        raw_timer=dict(timer_row),
    )
