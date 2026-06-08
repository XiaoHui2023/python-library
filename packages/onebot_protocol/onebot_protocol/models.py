from typing import Annotated, Any, Literal, Union
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def _optional_str(value: Any) -> str | None:
    """把标量转为去空白字符串；空串与 None 视为缺失。"""
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    text = str(value).strip()
    return text or None


class TextSegmentData(BaseModel):
    text: str = Field(description="纯文本")


class MentionSegmentData(BaseModel):
    user_id: str = Field(description="被 @ 的用户 ID")


class MentionAllSegmentData(BaseModel):
    pass


class FileData(BaseModel):
    name: str | None = Field(default=None, description="显示用文件名")
    content: str | None = Field(
        default=None,
        description="内容引用，如 URL、平台资源标识或 Base64 等，由实现方约定编码",
    )
    mime_type: str | None = Field(default=None, description="MIME 类型")
    size: int | None = Field(default=None, description="字节大小")


class ImageSegmentData(FileData):
    pass


class VoiceSegmentData(FileData):
    pass


class AudioSegmentData(FileData):
    pass


class VideoSegmentData(FileData):
    pass


class FileSegmentData(FileData):
    pass


class LocationSegmentData(BaseModel):
    latitude: float = Field(description="纬度")
    longitude: float = Field(description="经度")
    title: str = Field(description="位置标题")
    content: str = Field(description="位置说明")


class ReplySegmentData(BaseModel):
    message_id: str = Field(description="被回复的消息 ID")
    user_id: str | None = Field(default=None, description="被回复用户 ID")


class TextMessageSegment(BaseModel):
    type: Literal["text"] = "text"
    data: TextSegmentData


class MentionMessageSegment(BaseModel):
    type: Literal["mention"] = "mention"
    data: MentionSegmentData


class MentionAllMessageSegment(BaseModel):
    type: Literal["mention_all"] = "mention_all"
    data: MentionAllSegmentData = Field(default_factory=MentionAllSegmentData)


class ImageMessageSegment(BaseModel):
    type: Literal["image"] = "image"
    data: ImageSegmentData


class VoiceMessageSegment(BaseModel):
    type: Literal["voice"] = "voice"
    data: VoiceSegmentData


class AudioMessageSegment(BaseModel):
    type: Literal["audio"] = "audio"
    data: AudioSegmentData


class VideoMessageSegment(BaseModel):
    type: Literal["video"] = "video"
    data: VideoSegmentData


class FileMessageSegment(BaseModel):
    type: Literal["file"] = "file"
    data: FileSegmentData


class LocationMessageSegment(BaseModel):
    type: Literal["location"] = "location"
    data: LocationSegmentData


class ReplyMessageSegment(BaseModel):
    type: Literal["reply"] = "reply"
    data: ReplySegmentData


MessageSegment = Annotated[
    Union[
        TextMessageSegment,
        MentionMessageSegment,
        MentionAllMessageSegment,
        ImageMessageSegment,
        VoiceMessageSegment,
        AudioMessageSegment,
        VideoMessageSegment,
        FileMessageSegment,
        LocationMessageSegment,
        ReplyMessageSegment,
    ],
    Field(discriminator="type"),
]


class MessagePayload(BaseModel):
    """OneBot 11 消息事件载荷；消息段列表字段名为 ``message``。"""

    message_id: str = Field(default="", description="消息唯一 ID")
    post_type: str = Field(default="", description="事件类型，如 message")
    message_type: Literal["group", "private"] = Field(description="群聊或私聊")
    self_id: str = Field(default="", description="机器人 QQ 号")
    user_id: str | None = Field(default=None, description="发送方用户 ID；私聊时亦为会话对端")
    group_id: str | None = Field(default=None, description="群号；群聊会话标识")
    message: list[MessageSegment] = Field(description="消息段列表")

    @property
    def peer_id(self) -> str:
        """会话对端：群聊为 ``group_id``，私聊为 ``user_id``。"""
        if self.message_type == "group":
            return (self.group_id or "").strip()
        return (self.user_id or "").strip()

    @model_validator(mode="before")
    @classmethod
    def normalize_inbound_raw(cls, data: Any) -> Any:
        """归一标量类型，并兼容旧版统一字段名。"""
        if not isinstance(data, dict):
            return data
        raw = dict(data)

        if "messages" in raw and "message" not in raw:
            raw["message"] = raw.pop("messages")
        if "source_type" in raw and "message_type" not in raw:
            raw["message_type"] = raw.pop("source_type")
        if "bot_id" in raw and "self_id" not in raw:
            raw["self_id"] = raw.pop("bot_id")

        legacy_session = _optional_str(raw.pop("session_id", None))

        for key in ("message_id", "self_id", "post_type"):
            if key not in raw:
                continue
            text = _optional_str(raw[key])
            raw[key] = text if text is not None else ""

        for key in ("user_id", "group_id"):
            if key not in raw:
                continue
            text = _optional_str(raw[key])
            raw[key] = text

        message_type = _optional_str(raw.get("message_type"))
        if message_type not in ("group", "private") and raw.get("group_id") is not None:
            message_type = "group"
        if message_type in ("group", "private"):
            raw["message_type"] = message_type

        if legacy_session:
            effective_type = raw.get("message_type")
            if effective_type == "group" and not _optional_str(raw.get("group_id")):
                raw["group_id"] = legacy_session
            elif effective_type == "private" and not _optional_str(raw.get("user_id")):
                raw["user_id"] = legacy_session
            elif not _optional_str(raw.get("group_id")) and effective_type == "group":
                raw["group_id"] = legacy_session
            elif not _optional_str(raw.get("user_id")) and effective_type == "private":
                raw["user_id"] = legacy_session

        return raw

    def model_post_init(self, __context: Any) -> None:
        if not self.message_id:
            self.message_id = str(uuid4())
