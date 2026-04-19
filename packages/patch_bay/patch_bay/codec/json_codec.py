from __future__ import annotations

import json
from typing import Any


def dumps(obj: Any) -> bytes:
    """将对象序列化为 UTF-8 JSON 字节串。"""
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def loads(data: bytes) -> Any:
    """从 UTF-8 JSON 字节串反序列化。"""
    return json.loads(data.decode("utf-8"))
