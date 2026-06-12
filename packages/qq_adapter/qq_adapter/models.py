from dataclasses import dataclass, field
from enum import StrEnum


class QQSource(StrEnum):
    """QQ 开放平台会话场景。"""

    GUILD = "guild"
    GROUP = "group"
    C2C = "c2c"


# 网关事件名 → 会话场景
EVENT_SOURCE_MAP: dict[str, QQSource] = {
    "AT_MESSAGE_CREATE": QQSource.GUILD,
    "GROUP_AT_MESSAGE_CREATE": QQSource.GROUP,
    "C2C_MESSAGE_CREATE": QQSource.C2C,
}


@dataclass
class QQMediaAttachment:
    """QQ 富媒体发送前的本地附件描述。"""

    file_type: int
    """媒体类型：1 图片，2 视频，3 语音，4 文件。"""
    url: str = ""
    """远端媒体地址。"""
    file_data: str = ""
    """base64 编码的媒体二进制。"""
    name: str | None = None
    """显示文件名。"""
    mime_type: str | None = None
    """媒体 MIME 类型。"""


@dataclass
class QQMessage:
    """包内使用的 QQ 入站/出站消息结构。"""

    source_id: str
    """回复目标 ID，与 session_id 在入站时通常相同。"""
    session_id: str
    """会话标识，用于关联历史来源类型。"""
    msg_id: str
    """平台消息 ID，出站回复时作为被引用消息。"""
    content: str
    """平台正文，含标签语法。"""
    source_type: QQSource | None = None
    """频道、群或单聊；出站时未知则查运行期缓存。"""
    bot_id: str | None = None
    """机器人 ID。"""
    user_id: str | None = None
    """发送方用户 ID。"""
    media: list[QQMediaAttachment] = field(default_factory=list)
    """待发送的富媒体附件。"""
