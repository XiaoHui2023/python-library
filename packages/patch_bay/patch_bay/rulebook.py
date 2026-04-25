from __future__ import annotations

import json
from pathlib import Path


def load_rulebook_from_json_file(path: str | Path) -> dict[str, str]:
    """从独立 JSON 文件加载规则表。

    Args:
        path: 规则表 JSON 文件路径。

    Returns:
        dict[str, str]: 规则 id 到表达式字符串的映射。

    Raises:
        TypeError: JSON 根结构或键值类型不符合规则表要求。
    """
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise TypeError("rulebook JSON 顶层必须是 object")
    out: dict[str, str] = {}
    for k, v in data.items():
        if not isinstance(k, str):
            raise TypeError(f"rulebook 键必须是字符串: {k!r}")
        if not isinstance(v, str):
            raise TypeError(f"规则 {k!r} 的值必须是字符串表达式")
        out[k] = v
    return out


def merge_rulebook(*parts: dict[str, str]) -> dict[str, str]:
    """合并多段规则表。

    Args:
        *parts: 按优先级从低到高排列的规则表。

    Returns:
        dict[str, str]: 合并后的规则表；后出现的同名规则覆盖先出现的规则。
    """
    merged: dict[str, str] = {}
    for d in parts:
        merged.update(d)
    return merged
