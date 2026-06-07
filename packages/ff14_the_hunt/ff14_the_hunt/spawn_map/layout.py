from __future__ import annotations

from typing import Any

from ff14_the_hunt.models import SpawnMapLayout


def layout_from_spawn_entry(spawn_entry: dict[str, Any] | None) -> SpawnMapLayout | None:
    """从 ``SpawnPoint`` 条目解析站点格点与归一化参数。"""
    if not spawn_entry:
        return None
    dimensions = spawn_entry.get("Dimensions") or [41, 41]
    scale = float(dimensions[0]) if dimensions else 41.0
    size_y = float(dimensions[1]) if len(dimensions) > 1 else scale
    version = spawn_entry.get("Version")
    return SpawnMapLayout(
        grid_scale=scale,
        grid_size_x=scale,
        grid_size_y=size_y,
        display_points=int(spawn_entry.get("DisplayPoints", 0)),
        version=int(version) if version is not None else None,
    )
