from __future__ import annotations

from ff14_the_hunt.models import MapCoordinate


def select_display_spawn_points(points: list[MapCoordinate]) -> list[MapCoordinate]:
    """刚刷新记录上只展示仍可能触发的绿色候选点。"""
    active = [point for point in points if point.active is True]
    return active


def resolve_region_name(region: str | list[str]) -> str:
    """狩猎元数据 ``Region`` 字段转站点地图文件名。"""
    if isinstance(region, list):
        return region[0] if region else ""
    return region
