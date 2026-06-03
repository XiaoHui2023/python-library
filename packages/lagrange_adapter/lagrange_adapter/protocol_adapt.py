from typing import List, Union, Optional
from lagrange_adapter.models import (
    BaseSegment,
    TextSegment,
    ImageSegment,
    FaceSegment,
    AtSegment,
    ForwardSegment,
    ReplySegment,
    JsonSegment,
    VideoSegment,
    MfaceSegment,
    LocationSegment,
    BotMessage,
    MessageType,
)
import onebot_protocol
from onebot_protocol import MessagePayload

SEGMENT_MAP = {
    "text": TextSegment,
    "image": ImageSegment,
    "face": FaceSegment,
    "at": AtSegment,
    "forward": ForwardSegment,
    "reply": ReplySegment,
    "json": JsonSegment,
    "video": VideoSegment,
    "mface": MfaceSegment,
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
    """把对外统一载荷转成 CQ 段列表供 aiocqhttp 发送。

    Args:
        payload: 会话、消息段与机器人标识

    Returns:
        含 data_list 的包内机器人消息
    """
    data_list = []
    for message in payload.messages:
        if isinstance(message, onebot_protocol.TextMessageSegment):
            message = TextSegment(data={"text": message.data.text})
        elif isinstance(message, onebot_protocol.MentionMessageSegment):
            name = USER_MAP.get(message.data.user_id)
            if not name:
                continue
            message = AtSegment(data={"qq": message.data.user_id, "name": name})
        data_list.append(message.model_dump())

    msg = BotMessage(
        message_id=payload.message_id,
        data_list=data_list,
        message_type=MessageType(payload.source_type),
        bot_id=payload.bot_id,
        session_id=payload.session_id,
        user_name=payload.user_id or "",
    )

    if msg.message_type == MessageType.GROUP:
        if msg.user_name:
            msg.data_list = [
                AtSegment(data={"qq": msg.user_name, "name": USER_MAP.get(msg.user_name, "")}).model_dump(),
                TextSegment(data={"text": " "}).model_dump(),
            ] + msg.data_list

    return msg


def bot_to_onebot(msg: BotMessage) -> Optional[MessagePayload]:
    """把入站 CQ 消息转为对外统一载荷；群聊未 @ 机器人时返回空。

    Args:
        msg: 事件解析后的包内消息

    Returns:
        可上报的统一载荷；无需上报时为 None
    """
    global USER_MAP

    segments = data_to_segments(msg.data_list, msg.bot_name, msg.bot_id)

    if not _should_broadcast(msg, segments):
        return None

    for segment in segments:
        if isinstance(segment, AtSegment) and segment.qq == msg.bot_id:
            segments.remove(segment)

    messages = []
    for segment in segments:
        if isinstance(segment, TextSegment):
            text = segment.text.strip()
            if not text:
                continue
            message = onebot_protocol.TextMessageSegment(data={"text": text})
        elif isinstance(segment, AtSegment):
            if segment.name == MENTION_ALL_NAME:
                message = onebot_protocol.MentionAllMessageSegment()
            else:
                message = onebot_protocol.MentionMessageSegment(data={"user_id": segment.qq})
            USER_MAP[segment.qq] = segment.name
        else:
            continue
        messages.append(message)

    if not messages:
        return None

    return MessagePayload(
        message_id=msg.message_id,
        source_type=msg.message_type.value,
        bot_id=msg.bot_id,
        session_id=msg.session_id,
        user_id=msg.user_name,
        messages=messages,
    )


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
