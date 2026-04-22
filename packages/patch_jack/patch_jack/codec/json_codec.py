from __future__ import annotations

import json
from typing import Any


def dumps(obj: Any) -> bytes:
    """将对象序列化为 UTF-8 编码的 JSON 字节串。

    Args:
        obj: 可由标准库 JSON 编码器接受的 Python 对象。

    Returns:
        UTF-8 字节形式的 JSON。
    """
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def loads(data: bytes) -> Any:
    """从 UTF-8 JSON 字节串反序列化为 Python 对象。

    Args:
        data: 与本模块编码函数配对的 UTF-8 字节输入。

    Returns:
        解析后的 Python 值。
    """
    return json.loads(data.decode("utf-8"))
