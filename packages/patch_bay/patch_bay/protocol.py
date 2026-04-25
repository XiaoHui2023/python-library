from __future__ import annotations

from typing import Literal

import msgpack
from pydantic import BaseModel, ConfigDict, Field

FrameKind = Literal["hello", "send", "deliver", "ack", "error"]


class Frame(BaseModel):
    """有线层一帧：紧凑二进制编码；业务只关心载荷，不包含独立通道语义。"""

    model_config = ConfigDict(extra="ignore")

    kind: FrameKind = Field(description="语义类别：握手、出站、投递、确认或错误")
    address: str | None = Field(
        default=None,
        description="可选附带的文本地址；对端身份通常由传输层远端决定，握手时常为空",
    )
    payload: bytes | None = Field(default=None, description="业务数据或给人看的错误字节")
    seq: int | None = Field(
        default=None,
        description="可选单调序号，用于出站与确认之间的配对",
    )


def encode_frame(frame: Frame) -> bytes:
    """将一帧有线消息编码为紧凑二进制表示。

    Args:
        frame: 待发送的协议帧。

    Returns:
        bytes: 可放入长连接二进制消息体的字节串。
    """
    data = frame.model_dump(mode="python", exclude_none=True)
    return msgpack.packb(data, use_bin_type=True)


def decode_frame(raw: bytes) -> Frame:
    """从紧凑二进制表示还原协议帧。

    Args:
        raw: 线上收到的二进制载荷。

    Returns:
        Frame: 校验后的帧模型。

    Raises:
        ValueError: 根结构不是键值映射、无法对应帧模型时。
    """
    obj = msgpack.unpackb(raw, raw=False)
    if not isinstance(obj, dict):
        raise ValueError("frame root must be a mapping")
    return Frame.model_validate(obj)


def error_frame(message: str) -> Frame:
    """构造发往对端接入点的错误通知帧（说明文本以 UTF-8 置于载荷）。

    Args:
        message: 给人看的简短错误说明。

    Returns:
        Frame: 语义为错误、载荷为 UTF-8 文本字节的帧实例。
    """
    return Frame(kind="error", payload=message.encode("utf-8"))
