from __future__ import annotations

import json
from typing import Any


def build_packet_eval_scope(packet: bytes) -> dict[str, Any]:
    """构造面向规则表达式的数据包字段上下文。

    Args:
        packet: 传输中收到的原始载荷。

    Returns:
        dict[str, Any]: JSON 对象的顶层字段；不可解析或根不是对象时返回空字典。
    """
    try:
        text = packet.decode("utf-8")
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    return {}
