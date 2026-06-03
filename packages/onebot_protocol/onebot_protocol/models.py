from typing import Annotated, Any, Literal, Union
from uuid import uuid4

from pydantic import BaseModel, Field


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
    message_id: str = Field(default="", description="消息唯一 ID")
    source_type: Literal["group", "private"] = Field(description="会话类型")
    session_id: str = Field(description="会话 ID")
    bot_id: str = Field(default="", description="机器人 ID")
    user_id: str | None = Field(default=None, description="发送方用户 ID")
    messages: list[MessageSegment] = Field(description="消息段列表")
    post_type: str = Field(default="", description="事件类型")

    def model_post_init(self, __context: Any) -> None:
        if not self.message_id:
            self.message_id = str(uuid4())
