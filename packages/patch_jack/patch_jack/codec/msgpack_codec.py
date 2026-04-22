from __future__ import annotations

from typing import Any

import msgpack


def dumps(obj: Any) -> bytes:
    """将任意可序列化对象写成 msgpack 字节串。

    Args:
        obj: 由 msgpack 支持的 Python 对象图。

    Returns:
        二进制 msgpack 表示。
    """
    return msgpack.packb(obj, use_bin_type=True)


def loads(data: bytes) -> Any:
    """从 msgpack 字节串还原 Python 对象。

    Args:
        data: 与本模块编码函数配对的二进制输入。

    Returns:
        反序列化结果。
    """
    return msgpack.unpackb(data, raw=False)
