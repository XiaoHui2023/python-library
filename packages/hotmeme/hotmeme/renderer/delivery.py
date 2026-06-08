from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from hotmeme.renderer.content import ContentBlockKind, PostReference
from hotmeme.renderer.models import MemeOutputPacket


class OutboundImage(BaseModel):
    """单条消息内的一张图。"""

    model_config = ConfigDict(extra="forbid")

    data: bytes | None = Field(default=None, description="已下载图片二进制")
    content_type: str | None = Field(default=None, description="图片 MIME")
    url: str | None = Field(default=None, description="未下载时的远程地址")


class OutboundMessage(BaseModel):
    """一条对外发送的消息：多图与正文不得拆成多条。"""

    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(description="对应 ImageItem.id")
    title: str = Field(description="标题摘要")
    images: list[OutboundImage] = Field(
        default_factory=list,
        description="本条消息内的全部图片，按图集顺序",
    )
    text: str | None = Field(default=None, description="本条消息正文")
    reference: PostReference = Field(description="作者与原帖链，不属于正文")


def message_from_packet(packet: MemeOutputPacket) -> OutboundMessage:
    """从输出包提取单条对外消息视图。"""
    images: list[OutboundImage] = []
    text: str | None = None
    for block in packet.content.blocks:
        if block.kind == ContentBlockKind.IMAGE:
            images.append(
                OutboundImage(
                    data=block.data,
                    content_type=block.content_type,
                    url=block.url,
                ),
            )
            continue
        if block.kind == ContentBlockKind.TEXT:
            text = block.text
    return OutboundMessage(
        item_id=packet.item_id,
        title=packet.title,
        images=images,
        text=text,
        reference=packet.reference,
    )
