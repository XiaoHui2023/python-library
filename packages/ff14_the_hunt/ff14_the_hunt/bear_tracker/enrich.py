from __future__ import annotations

import time
from typing import Any

from ff14_the_hunt.models import HuntMarkRecord, HuntQueryFilter

from ff14_the_hunt.bear_tracker.fate_timer import compute_fate_timer
from ff14_the_hunt.bear_tracker.resources import BearResources
from ff14_the_hunt.bear_tracker.spawn_window import (
    compute_trigger_timer,
)


def mark_has_display_timer(record: HuntMarkRecord) -> bool:
    """记录是否带有站点主列表会展示的任一条计时。"""
    return (
        record.trigger_timer is not None
        or record.condition_timer is not None
        or record.fate_timer is not None
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

    fate_timer = compute_fate_timer(
        fate_last_seen=timer_row.get("fateLastSeen"),
        fate_last_death=timer_row.get("fateLastDeath"),
        now=now,
    )

    recently = False
    if last_mark:
        reference_now = time.time() if now is None else now
        recently = reference_now - float(last_mark) <= recent_grace_seconds

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
        condition_timer=None,
        fate_timer=fate_timer,
        recently_spawned=recently,
        raw_timer=dict(timer_row),
    )
