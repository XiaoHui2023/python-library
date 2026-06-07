from __future__ import annotations

import re
from typing import Any

from ff14_the_hunt.models import MapCoordinate


def list_map_coordinates(
    spawn_entry: dict[str, Any] | None,
    *,
    api_states: dict[str, Any] | None = None,
) -> list[MapCoordinate]:
    """从 ``resources.SpawnPoint`` 条目解析触发生点坐标。

    Args:
        spawn_entry: ``syncSession`` 内 ``SpawnPoint[huntKey]``。
        api_states: ``querySpawnPoints`` 返回的各点状态（可选）。
    """
    if not spawn_entry:
        return []
    dimensions = spawn_entry.get("Dimensions") or [41, 41]
    scale = float(dimensions[0]) if dimensions else 41.0
    display_count = int(spawn_entry.get("DisplayPoints", 0))
    coordinates: list[MapCoordinate] = []
    point_items = sorted(
        (
            (key, value)
            for key, value in spawn_entry.items()
            if re.match(r"^SpawnPoint\d+$", key)
        ),
        key=lambda item: item[0],
    )
    for index, (key, raw) in enumerate(point_items):
        if display_count and index >= display_count:
            break
        if not isinstance(raw, (list, tuple)) or len(raw) < 2:
            continue
        grid_x = float(raw[0])
        grid_y = float(raw[1])
        norm_x = (grid_x - 1.0) / scale
        norm_y = (grid_y - 1.0) / scale
        state = None
        if api_states and key in api_states:
            entry = api_states[key]
            if isinstance(entry, dict):
                state_val = entry.get("State")
                if state_val is not None:
                    state = bool(state_val)
        coordinates.append(
            MapCoordinate(
                point_key=key,
                x=norm_x,
                y=norm_y,
                grid_x=grid_x,
                grid_y=grid_y,
                active=state,
            )
        )
    return coordinates
