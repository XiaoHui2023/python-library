from __future__ import annotations

from typing import Any

import msgpack


def dumps(obj: Any) -> bytes:
    """将对象序列化为 msgpack 字节串。"""
    return msgpack.packb(obj, use_bin_type=True)


def loads(data: bytes) -> Any:
    """从 msgpack 字节串反序列化。"""
    return msgpack.unpackb(data, raw=False)
