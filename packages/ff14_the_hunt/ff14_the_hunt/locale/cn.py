from __future__ import annotations

from ff14_the_hunt.locale.names import translate_hunt_name, translate_region
from ff14_the_hunt.locale.tag import HuntDisplayLocale
from ff14_the_hunt.locale.spawn_map_display import (
    region_map_to_display_dict_zh,
    spawn_layout_to_display_dict_zh,
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

PATCH_CODE_TO_CN: dict[str, str] = {
    "ARR": "重生之境",
    "HW": "苍穹之禁城",
    "ShB": "红莲之狂潮",
    "EW": "晓月的终途",
    "DT": "金曦之遗辉",
}

PATCH_CN_TO_CODE: dict[str, str] = {cn: code for code, cn in PATCH_CODE_TO_CN.items()}

RANK_KIND_TO_CN: dict[HuntRankKind, str] = {
    HuntRankKind.A: "A级",
    HuntRankKind.S: "S级",
    HuntRankKind.FATE: "FATE",
}

TIMER_KIND_TO_CN: dict[TimerKind, str] = {
    TimerKind.TRIGGER: "触发时间",
    TimerKind.CONDITION: "条件时间",
    TimerKind.FATE: "FATE",
}

PHASE_TO_CN: dict[SpawnWindowPhase, str] = {
    SpawnWindowPhase.CLOSED: "未满足",
    SpawnWindowPhase.ALMOST_OPEN: "即将开窗",
    SpawnWindowPhase.OPEN: "开窗中",
    SpawnWindowPhase.CAPPED: "强制期",
}


def normalize_patch_codes(patches: list[str]) -> list[str]:
    """将资料片中文名或 Bear Tracker 缩写统一为内部 Patch 代码。"""
    normalized: list[str] = []
    for item in patches:
        text = item.strip()
        if not text:
            continue
        code = PATCH_CN_TO_CODE.get(text, text)
        if code not in normalized:
            normalized.append(code)
    return normalized


def patch_code_to_cn(code: str) -> str:
    return PATCH_CODE_TO_CN.get(code, code)


def query_to_display_dict(query: HuntQueryFilter) -> dict[str, object]:
    """将筛选条件序列化为中文配置视图。"""
    payload: dict[str, object] = {
        "数据中心": list(query.data_centers),
        "世界": list(query.worlds),
        "狩猎等级": [RANK_KIND_TO_CN.get(kind, kind.value) for kind in query.rank_kinds],
    }
    if query.patches:
        payload["资料片"] = [patch_code_to_cn(code) for code in query.patches]
    if query.hunt_keys:
        payload["限定狩猎"] = list(query.hunt_keys)
    if query.regions:
        payload["地图区域"] = list(query.regions)
    payload["含无计时占位"] = query.include_untimed_marks
    return payload


def _timer_to_display_dict(timer: TimerDisplay | None) -> dict[str, object] | None:
    if timer is None:
        return None
    item: dict[str, object] = {
        "种类": TIMER_KIND_TO_CN.get(timer.kind, timer.kind.value),
        "简述": timer.summary,
        "条颜色": timer.bar_color.value,
        "色值": timer.hex_color,
        "正计时": timer.counts_up,
    }
    if timer.phase is not None:
        item["阶段"] = PHASE_TO_CN.get(timer.phase, timer.phase.value)
    if timer.elapsed_seconds is not None:
        item["已过秒数"] = timer.elapsed_seconds
    if timer.remaining_seconds is not None:
        item["剩余秒数"] = timer.remaining_seconds
    if timer.progress_percent is not None:
        item["进度百分比"] = timer.progress_percent
    return item


def mark_to_display_dict(
    mark: HuntMarkRecord,
    *,
    embed_region_map_data: bool = True,
    region_map_file_name: str | None = None,
) -> dict[str, object]:
    """将单条狩猎记录序列化为中文视图。"""
    locale = HuntDisplayLocale.ZH
    region_text = translate_region(mark.region, locale)

    item: dict[str, object] = {
        "狩猎键": mark.hunt_key,
        "狩猎名": translate_hunt_name(mark.hunt_key, locale),
        "世界": mark.world_name,
        "地图区域": region_text,
        "资料片": patch_code_to_cn(mark.patch),
        "等级": mark.rank,
        "上次死亡时间": mark.last_death_time,
        "上次标记时间": mark.last_mark_time,
        "失踪计数": mark.missing_counter,
        "维护计时": mark.is_maintenance,
        "刚刷新": mark.recently_spawned,
        "新检出": mark.newly_spawned,
    }
    if mark.fate_last_seen is not None:
        item["FATE最近发现"] = mark.fate_last_seen
    if mark.fate_last_death is not None:
        item["FATE上次死亡"] = mark.fate_last_death

    trigger = _timer_to_display_dict(mark.trigger_timer)
    if trigger is not None:
        item["触发计时"] = trigger
    condition = _timer_to_display_dict(mark.condition_timer)
    if condition is not None:
        item["条件计时"] = condition
    fate = _timer_to_display_dict(mark.fate_timer)
    if fate is not None:
        item["FATE计时"] = fate

    if mark.spawn_map_layout is not None:
        item["地图布局"] = spawn_layout_to_display_dict_zh(mark.spawn_map_layout)
    if mark.spawn_points:
        item["刷点"] = [
            {
                "点位": point.point_key,
                "地图X": point.x,
                "地图Y": point.y,
                "像素X": point.pixel_x,
                "像素Y": point.pixel_y,
                "格点X": point.grid_x,
                "格点Y": point.grid_y,
                "存活": point.active,
            }
            for point in mark.spawn_points
        ]
    if mark.region_map is not None:
        item["区域地图"] = region_map_to_display_dict_zh(
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
    """将单次爬取结果序列化为中文配置与怪物列表。"""
    file_names = region_map_file_names or {}

    def _mark_dict(mark: HuntMarkRecord) -> dict[str, object]:
        key = (mark.hunt_key, mark.world_name)
        return mark_to_display_dict(
            mark,
            embed_region_map_data=embed_region_map_data,
            region_map_file_name=file_names.get(key),
        )

    payload: dict[str, object] = {
        "配置": query_to_display_dict(packet.query),
        "爬取时间": packet.crawled_at,
        "下次爬取时间": packet.next_fetch_at,
        "怪物": [_mark_dict(mark) for mark in packet.marks],
    }
    if recently_spawned is not None:
        payload["刚刷新"] = [_mark_dict(mark) for mark in recently_spawned]
    return payload
