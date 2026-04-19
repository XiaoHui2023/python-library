from __future__ import annotations

import json
from typing import Any


def build_packet_eval_scope(packet: bytes) -> dict[str, Any]:
    """express_evaluator 求值上下文：以传输中的数据包为核心。

    提供 `packet`（bytes）、`packet_type`、`packet_len`；若 UTF-8 JSON 可解析则提供 `json` 与 `data`（dict 时）。
    """
    scope: dict[str, Any] = {
        "packet": packet,
        "packet_type": type(packet).__name__,
        "packet_len": len(packet),
    }
    scope["json"] = None
    scope["data"] = None
    try:
        text = packet.decode("utf-8")
        obj = json.loads(text)
        scope["json"] = obj
        if isinstance(obj, dict):
            scope["data"] = obj
    except Exception:
        pass
    return scope
