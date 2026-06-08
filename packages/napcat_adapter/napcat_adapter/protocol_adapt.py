from typing import List, Union, Optional

import onebot_protocol
from onebot_protocol import MessagePayload
from onebot_protocol.models import (
    FileSegmentData,
    ImageSegmentData,
    LocationSegmentData,
    ReplySegmentData,
    VideoSegmentData,
    VoiceSegmentData,
)

from napcat_adapter.models import (
    AtSegment,
    BaseSegment,
    BotMessage,
    FileSegment,
    ImageSegment,
    LocationSegment,
    MessageType,
    RecordSegment,
    ReplySegment,
    TextSegment,
    VideoSegment,
)

SEGMENT_MAP = {
    "text": TextSegment,
    "image": ImageSegment,
    "record": RecordSegment,
    "file": FileSegment,
    "at": AtSegment,
    "reply": ReplySegment,
    "video": VideoSegment,
    "location": LocationSegment,
}

USER_MAP: dict[str, str] = {}

MENTION_ALL_NAME = "全体成员"


def data_to_segments(data_list: list[dict], bot_name: str, bot_id: str) -> list[BaseSegment]:
    """把原始段字典列表转为强类型段，并拆分正文里的 @ 机器人。

    Args:
        data_list: 事件中的 CQ 段列表
        bot_name: 机器人昵称，用于匹配 @
        bot_id: 机器人 QQ 号

    Returns:
        过滤无效项并展开 @ 后的段列表
    """
    segments = [_cast_segment(x) for x in data_list]
    segments = [x for x in segments if x]

    segments = [
        (_extract_mention_robot(x, bot_name, bot_id) if isinstance(x, TextSegment) else [x])
        for x in segments
    ]
    segments = [x for data in segments for x in data]

    return segments


def onebot_to_bot(payload: MessagePayload) -> BotMessage:
    """把对外统一载荷转成 NapCat 可发送的 CQ 段列表。

    Args:
        payload: 会话、消息段与机器人标识

    Returns:
        含 data_list 的包内机器人消息
    """
    data_list = []
    for segment in payload.message:
        cq_segment = _onebot_to_cq_segment(segment)
        if cq_segment is None:
            continue
        data_list.append(cq_segment.model_dump())

    return BotMessage(
        message_id=payload.message_id,
        data_list=data_list,
        message_type=MessageType(payload.message_type),
        bot_id=payload.self_id,
        session_id=payload.peer_id,
        user_name=payload.user_id or "",
    )


def bot_to_onebot(msg: BotMessage) -> Optional[MessagePayload]:
    """把 NapCat 入站消息转为对外统一载荷；群聊未 @ 机器人时返回空。

    Args:
        msg: 事件解析后的包内消息

    Returns:
        可上报的统一载荷；无需上报时为 None
    """
    global USER_MAP

    segments = data_to_segments(msg.data_list, msg.bot_name, msg.bot_id)

    if not _should_broadcast(msg, segments):
        return None

    segments = [s for s in segments if not (isinstance(s, AtSegment) and s.qq == msg.bot_id)]

    messages = []
    for segment in segments:
        if isinstance(segment, AtSegment) and segment.qq:
            USER_MAP[segment.qq] = segment.name or ""
        converted = _segment_to_onebot(segment)
        if converted is not None:
            messages.append(converted)

    if not messages:
        return None

    is_group = msg.message_type == MessageType.GROUP
    return MessagePayload(
        message_id=msg.message_id,
        message_type=msg.message_type.value,
        self_id=msg.bot_id,
        group_id=msg.session_id if is_group else None,
        user_id=msg.user_name,
        message=messages,
    )


def _cq_data_to_file_data(data: dict) -> Optional[FileSegmentData]:
    """从 CQ data 提取 FileData；无可用内容引用时返回 None。"""
    content = data.get("url") or data.get("file") or data.get("path")
    if not content:
        return None
    name = data.get("name") or data.get("filename")
    mime_type = data.get("mime") or data.get("mime_type")
    raw_size = data.get("file_size", data.get("size"))
    size: int | None = None
    if raw_size is not None:
        try:
            size = int(raw_size)
        except (TypeError, ValueError):
            size = None
    return FileSegmentData(name=name, content=str(content), mime_type=mime_type, size=size)


def _file_data_to_cq(data: FileSegmentData) -> dict:
    """把 FileData 编成 NapCat / OneBot 11 可识别的 CQ data。"""
    out: dict = {}
    content = data.content
    if not content:
        return out
    out["file"] = content
    if content.startswith(("http://", "https://")):
        out["url"] = content
    if data.name:
        out["name"] = data.name
    if data.size is not None:
        out["file_size"] = data.size
    return out


def _onebot_to_cq_segment(
    message: onebot_protocol.MessageSegment,
) -> BaseSegment | None:
    if isinstance(message, onebot_protocol.TextMessageSegment):
        return TextSegment(data={"text": message.data.text})
    if isinstance(message, onebot_protocol.MentionMessageSegment):
        name = USER_MAP.get(message.data.user_id, "")
        return AtSegment(data={"qq": message.data.user_id, "name": name})
    if isinstance(message, onebot_protocol.ImageMessageSegment):
        cq_data = _file_data_to_cq(message.data)
        return ImageSegment(data=cq_data) if cq_data else None
    if isinstance(message, onebot_protocol.VoiceMessageSegment):
        cq_data = _file_data_to_cq(message.data)
        return RecordSegment(data=cq_data) if cq_data else None
    if isinstance(message, onebot_protocol.AudioMessageSegment):
        cq_data = _file_data_to_cq(message.data)
        return FileSegment(data=cq_data) if cq_data else None
    if isinstance(message, onebot_protocol.VideoMessageSegment):
        cq_data = _file_data_to_cq(message.data)
        return VideoSegment(data=cq_data) if cq_data else None
    if isinstance(message, onebot_protocol.FileMessageSegment):
        cq_data = _file_data_to_cq(message.data)
        return FileSegment(data=cq_data) if cq_data else None
    if isinstance(message, onebot_protocol.LocationMessageSegment):
        loc = message.data
        return LocationSegment(
            data={
                "lat": loc.latitude,
                "lon": loc.longitude,
                "title": loc.title,
                "content": loc.content,
            }
        )
    if isinstance(message, onebot_protocol.ReplyMessageSegment):
        reply_id = message.data.message_id
        if not reply_id:
            return None
        return ReplySegment(data={"id": reply_id})
    return None


def _segment_to_onebot(
    segment: BaseSegment,
) -> onebot_protocol.MessageSegment | None:
    if isinstance(segment, TextSegment):
        text = (segment.text or "").strip()
        if not text:
            return None
        return onebot_protocol.TextMessageSegment(data={"text": text})
    if isinstance(segment, AtSegment):
        if segment.name == MENTION_ALL_NAME:
            return onebot_protocol.MentionAllMessageSegment()
        return onebot_protocol.MentionMessageSegment(data={"user_id": segment.qq})
    if isinstance(segment, ImageSegment):
        file_data = _cq_data_to_file_data(segment.data)
        if file_data is None:
            return None
        return onebot_protocol.ImageMessageSegment(data=ImageSegmentData(**file_data.model_dump()))
    if isinstance(segment, RecordSegment):
        file_data = _cq_data_to_file_data(segment.data)
        if file_data is None:
            return None
        return onebot_protocol.VoiceMessageSegment(data=VoiceSegmentData(**file_data.model_dump()))
    if isinstance(segment, VideoSegment):
        file_data = _cq_data_to_file_data(segment.data)
        if file_data is None:
            return None
        return onebot_protocol.VideoMessageSegment(data=VideoSegmentData(**file_data.model_dump()))
    if isinstance(segment, FileSegment):
        file_data = _cq_data_to_file_data(segment.data)
        if file_data is None:
            return None
        return onebot_protocol.FileMessageSegment(data=FileSegmentData(**file_data.model_dump()))
    if isinstance(segment, LocationSegment):
        raw = segment.data
        try:
            lat = float(raw.get("lat", 0))
            lon = float(raw.get("lon", 0))
        except (TypeError, ValueError):
            return None
        return onebot_protocol.LocationMessageSegment(
            data=LocationSegmentData(
                latitude=lat,
                longitude=lon,
                title=str(raw.get("title") or ""),
                content=str(raw.get("content") or ""),
            )
        )
    if isinstance(segment, ReplySegment):
        reply_id = segment.data.get("id")
        if not reply_id:
            return None
        return onebot_protocol.ReplyMessageSegment(
            data=ReplySegmentData(message_id=str(reply_id))
        )
    return None


def _should_broadcast(msg: BotMessage, segments: list[BaseSegment]) -> bool:
    """群聊仅在 @ 到机器人时向上层上报。"""
    if msg.message_type == MessageType.GROUP:
        for segment in segments:
            if isinstance(segment, AtSegment) and segment.qq == msg.bot_id:
                return True
        return False
    return True


def _cast_segment(data: dict) -> Optional[BaseSegment]:
    """按 type 字段实例化对应段模型；未知或校验失败返回 None。"""
    cls = SEGMENT_MAP.get(data["type"])
    if not cls:
        return None
    try:
        return cls(**data)
    except Exception:
        return None


def _extract_mention_robot(
    text: TextSegment, bot_name: str, bot_id: str
) -> List[Union[TextSegment, AtSegment]]:
    """把正文中「@昵称 」拆成文本段与 @ 段。"""

    def split(text: TextSegment) -> List[Union[TextSegment, AtSegment]]:
        content = text.text

        keyword = f"@{bot_name} "
        if keyword in content:
            index = content.find(keyword)
            before_text = content[:index]
            after_text = content[index + len(keyword):]
            return (
                split(TextSegment(data={"text": before_text}))
                + [AtSegment(data={"name": bot_name, "qq": bot_id})]
                + split(TextSegment(data={"text": after_text}))
            )
        return [text]

    try:
        return split(text)
    except Exception:
        return [text]
