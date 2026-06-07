from enum import StrEnum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class MessageType(StrEnum):
    """会话类型：私聊或群聊。"""

    PRIVATE = "private"
    GROUP = "group"


class BaseSegment(BaseModel):
    """CQ 消息段通用壳：类型名与原始数据字典。"""

    type: str = Field(description="段类型，如 text、at、image")
    data: dict = Field(description="协议原始字段字典")


class AtSegment(BaseSegment):
    """@ 成员段。"""

    type: Literal["at"] = "at"
    qq: str | None = None
    name: str | None = None

    def model_post_init(self, ctx) -> None:
        self.qq = self.data["qq"]
        raw_name = self.data.get("name") or ""
        self.name = raw_name.lstrip("@").strip()


class FaceSegment(BaseSegment):
    """QQ 表情段。"""

    type: Literal["face"] = "face"
    id: str | None = None
    large: str | None = None
    result_id: str | None = None
    chain_count: int | None = None

    def model_post_init(self, ctx) -> None:
        self.id = str(self.data["id"])
        self.large = self.data.get("large")
        self.result_id = self.data.get("resultId")
        self.chain_count = self.data.get("chainCount")


class TextSegment(BaseSegment):
    """纯文本段。"""

    type: Literal["text"] = "text"
    text: str | None = None

    def model_post_init(self, ctx) -> None:
        self.text = self.data["text"]


class ReplySegment(BaseSegment):
    """引用回复段。"""

    type: Literal["reply"] = "reply"
    id: str | None = None

    def model_post_init(self, ctx) -> None:
        self.id = self.data["id"]


class MfaceSegment(BaseSegment):
    """商城表情段。"""

    type: Literal["mface"] = "mface"
    url: str | None = None
    emoji_package_id: str | None = None
    emoji_id: str | None = None
    key: str | None = None
    summary: str | None = None


class LocationSegment(BaseSegment):
    """位置段。"""

    type: Literal["location"] = "location"
    lat: float | None = None
    lon: float | None = None
    title: str | None = None
    content: str | None = None


class JsonSegment(BaseSegment):
    """JSON 卡片段。"""

    type: Literal["json"] = "json"


class ImageSegment(BaseSegment):
    """图片段。"""

    type: Literal["image"] = "image"


class RecordSegment(BaseSegment):
    """语音段（CQ record）。"""

    type: Literal["record"] = "record"


class FileSegment(BaseSegment):
    """文件段。"""

    type: Literal["file"] = "file"


class ForwardSegment(BaseSegment):
    """合并转发段。"""

    type: Literal["forward"] = "forward"
    id: str | None = None


class VideoSegment(BaseSegment):
    """视频段。"""

    type: Literal["video"] = "video"


Segment = Annotated[
    Union[
        TextSegment,
        ImageSegment,
        RecordSegment,
        FileSegment,
        FaceSegment,
        AtSegment,
        ForwardSegment,
        ReplySegment,
        JsonSegment,
        VideoSegment,
        MfaceSegment,
        LocationSegment,
    ],
    Field(discriminator="type"),
]


class BotMessage(BaseModel):
    """包内入站/出站消息：CQ 段列表与会话上下文。"""

    message_id: str = Field(description="平台分配的消息编号")
    data_list: list[dict] = Field(description="CQ 协议段列表，每项含 type 与 data")
    message_type: MessageType = Field(description="私聊或群聊")
    bot_id: str = Field(description="当前机器人 QQ 号")
    bot_name: str | None = Field(default=None, description="机器人昵称，用于解析 @")
    session_id: str = Field(description="群号或好友号，用作发送目标")
    user_name: str = Field(description="发送方 QQ 号")


__all__ = [
    "BotMessage",
    "BaseSegment",
    "TextSegment",
    "ImageSegment",
    "RecordSegment",
    "FileSegment",
    "FaceSegment",
    "AtSegment",
    "ForwardSegment",
    "ReplySegment",
    "JsonSegment",
    "VideoSegment",
    "MfaceSegment",
    "LocationSegment",
    "MessageType",
    "Segment",
]
