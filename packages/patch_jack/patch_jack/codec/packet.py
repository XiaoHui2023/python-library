from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from .msgpack_codec import dumps as msgpack_dumps, loads as msgpack_loads


def encode_application_packet(packet: object) -> bytes:
    """将业务对象编码为可嵌入有线帧载荷的紧凑二进制串。

    Args:
        packet: 映射、带声明式校验的模型实例，或普通数据类实例等受支持形态。

    Returns:
        可嵌入出站业务帧载荷的二进制串。

    Raises:
        TypeError: 对象类型不在支持列表内时。
    """
    if isinstance(packet, Mapping):
        return msgpack_dumps(dict(packet))
    if isinstance(packet, BaseModel):
        return msgpack_dumps(packet.model_dump(mode="python"))
    if dataclasses.is_dataclass(packet) and not isinstance(packet, type):
        return msgpack_dumps(dataclasses.asdict(packet))
    raise TypeError(
        "业务包须为映射、带声明式校验的模型实例或数据类实例，"
        f"收到 {type(packet)!r}"
    )


def decode_application_packet(data: bytes) -> Any:
    """将紧凑二进制载荷还原为常见 Python 对象（多为映射）。

    Args:
        data: 取自投递类帧中的应用层字节块。

    Returns:
        解码后的 Python 值。
    """
    return msgpack_loads(data)
