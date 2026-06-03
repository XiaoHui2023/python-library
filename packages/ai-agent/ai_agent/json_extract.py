from __future__ import annotations

import json
import re
from typing import Any

_JSON_DECODER = json.JSONDecoder()

_FENCE_RE = re.compile(
    r"```(?:json)?\s*([\s\S]*?)\s*```",
    re.IGNORECASE,
)


def extract_first_json_value(text: str) -> Any | None:
    """
    从可能含说明文字、围栏或多个 JSON 的文本中解析第一个完整 JSON 值。

    Args:
        text: 模型原始输出

    Returns:
        解析到的对象或数组；无法解析时为 None
    """
    stripped = text.strip()
    if not stripped:
        return None
    candidates: list[str] = []
    for match in _FENCE_RE.finditer(stripped):
        inner = match.group(1).strip()
        if inner:
            candidates.append(inner)
    candidates.append(stripped)
    for candidate in candidates:
        value = _decode_first_json(candidate)
        if value is not None:
            return value
    return None


def extract_first_json_object(text: str) -> dict[str, Any] | None:
    """
    解析第一个 JSON 对象（dict）。

    Args:
        text: 模型原始输出

    Returns:
        根节点为对象时返回该 dict，否则 None
    """
    value = extract_first_json_value(text)
    if isinstance(value, dict):
        return value
    return None


def _decode_first_json(text: str) -> Any | None:
    idx = 0
    length = len(text)
    while idx < length:
        ch = text[idx]
        if ch in "{[":
            try:
                value, _end = _JSON_DECODER.raw_decode(text, idx)
            except json.JSONDecodeError:
                idx += 1
                continue
            return value
        idx += 1
    return None
