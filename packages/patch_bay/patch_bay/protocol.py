from __future__ import annotations

from typing import Literal

import msgpack
from pydantic import BaseModel, ConfigDict, Field

FrameKind = Literal["hello", "send", "deliver", "ack", "error"]


class Frame(BaseModel):
    """Jack ↔ PatchBay 有线协议的一帧（msgpack 编码）；业务仅搬运 payload，无通道概念。"""

    model_config = ConfigDict(extra="ignore")

    kind: FrameKind = Field(description="帧类型：握手、发送、投递、确认或错误")
    address: str | None = Field(
        default=None,
        description="可选；Jack 身份以 TCP 远端 host:port 为准，hello 通常不携带",
    )
    payload: bytes | None = Field(default=None, description="业务数据包或错误信息")
    seq: int | None = Field(default=None, description="可选序号，用于 send/ack 配对")


def encode_frame(frame: Frame) -> bytes:
    """将帧编码为 msgpack 字节串。"""
    data = frame.model_dump(mode="python", exclude_none=True)
    return msgpack.packb(data, use_bin_type=True)


def decode_frame(raw: bytes) -> Frame:
    """从 msgpack 字节串解码帧。"""
    obj = msgpack.unpackb(raw, raw=False)
    if not isinstance(obj, dict):
        raise ValueError("frame root must be a mapping")
    return Frame.model_validate(obj)


def error_frame(message: str) -> Frame:
    """构造发往 Jack 的错误帧（payload 为 UTF-8 文本）。"""
    return Frame(kind="error", payload=message.encode("utf-8"))
