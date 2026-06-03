from onebot_protocol import MessagePayload

from qq_adapter.models import QQMessage, QQSource
from qq_adapter.parse_tag import content_to_messages, messages_to_content


def onebot_to_qq(payload: MessagePayload) -> QQMessage:
    """把对外统一载荷压成 QQ 平台可发送的正文结构。

    Args:
        payload: 会话、消息段与机器人标识

    Returns:
        含平台正文字符串的包内消息对象
    """
    source_type: QQSource | None = None
    if payload.source_type == "private":
        source_type = QQSource.C2C
    return QQMessage(
        source_id=payload.session_id,
        session_id=payload.session_id,
        msg_id=payload.message_id,
        content=messages_to_content(payload.messages),
        source_type=source_type,
        bot_id=payload.bot_id,
        user_id=payload.user_id,
    )


def qq_to_onebot(msg: QQMessage) -> MessagePayload:
    """把 QQ 入站消息展开为对外统一载荷。

    Args:
        msg: 网关事件解析后的包内消息

    Returns:
        群聊与频道映射为 group，单聊映射为 private
    """
    if msg.source_type in [QQSource.GUILD, QQSource.GROUP]:
        source_type = "group"
    else:
        source_type = "private"

    return MessagePayload(
        message_id=msg.msg_id,
        source_type=source_type,
        bot_id=msg.bot_id or "",
        session_id=msg.source_id,
        user_id=msg.user_id,
        messages=content_to_messages(msg.content),
    )
