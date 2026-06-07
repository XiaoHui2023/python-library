from __future__ import annotations

import base64
import re
from pathlib import Path

from ff14_the_hunt.models import HuntMarkRecord


def _safe_map_basename(hunt_key: str, world_name: str) -> str:
    raw = f"{hunt_key}_{world_name}"
    cleaned = re.sub(r"[^\w.\-]+", "_", raw, flags=re.UNICODE)
    return cleaned.strip("_") or "region_map"


def write_region_map_files(
    marks: list[HuntMarkRecord],
    out_dir: Path,
) -> dict[tuple[str, str], str]:
    """将 ``region_map`` 原图解码为 PNG 文件。

    Returns:
        ``(hunt_key, world_name) -> 相对 out_dir 的路径``。
    """
    map_dir = out_dir / "maps"
    map_dir.mkdir(parents=True, exist_ok=True)
    names: dict[tuple[str, str], str] = {}
    for mark in marks:
        if mark.region_map is None:
            continue
        file_name = f"{_safe_map_basename(mark.hunt_key, mark.world_name)}.png"
        path = map_dir / file_name
        path.write_bytes(base64.b64decode(mark.region_map.data_base64))
        names[(mark.hunt_key, mark.world_name)] = f"maps/{file_name}"
    return names
