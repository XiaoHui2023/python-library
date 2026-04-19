from __future__ import annotations

import json
from pathlib import Path


def load_rulebook_from_json_file(path: str | Path) -> dict[str, str]:
    """从独立 JSON 文件加载规则：键为 rule_id，值为 express_evaluator 表达式字符串。"""
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
    """合并多段规则表，后者覆盖同名键。"""
    merged: dict[str, str] = {}
    for d in parts:
        merged.update(d)
    return merged
