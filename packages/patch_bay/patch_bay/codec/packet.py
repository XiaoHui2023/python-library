from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from .msgpack_codec import dumps as msgpack_dumps, loads as msgpack_loads


def encode_application_packet(packet: object) -> bytes:
    """将业务数据包编码为置于 Frame.payload 中的字节串（msgpack）。"""
    if isinstance(packet, Mapping):
        return msgpack_dumps(dict(packet))
    if isinstance(packet, BaseModel):
        return msgpack_dumps(packet.model_dump(mode="python"))
    if dataclasses.is_dataclass(packet) and not isinstance(packet, type):
        return msgpack_dumps(dataclasses.asdict(packet))
    raise TypeError(
        "send() 需要 dict/Mapping、Pydantic BaseModel 或 dataclass 实例作为数据包，"
        f"收到 {type(packet)!r}"
    )


def decode_application_packet(data: bytes) -> Any:
    """从 Frame.payload 解码为 Python 对象（通常为 dict）。"""
    return msgpack_loads(data)
