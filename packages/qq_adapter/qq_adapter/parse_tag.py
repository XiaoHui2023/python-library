import re
from collections.abc import Callable

from onebot_protocol import (
    ImageMessageSegment,
    MessageSegment,
    TextMessageSegment,
)


def parse_tag_attrs(tag_content: str) -> dict[str, str]:
    """解析尖括号标签内的键值对。

    Args:
        tag_content: 标签内部文本，不含外层尖括号

    Returns:
        属性名到取值的映射
    """
    attrs: dict[str, str] = {}
    for m in re.finditer(r'(\w+)=("(?:[^"\\]|\\.)*"|[^,]+)', tag_content):
        key, val = m.group(1), m.group(2).strip()
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1].replace('\\"', '"')
        attrs[key] = val
    return attrs


TagHandler = Callable[[dict[str, str]], MessageSegment | None]


def _parse_face(attrs: dict[str, str]) -> MessageSegment | None:
    """表情类标签：当前统一协议无对应段，忽略。"""
    return None


def _parse_image(attrs: dict[str, str]) -> MessageSegment | None:
    """图片类标签：有地址或文件标识时转为图片段。

    Args:
        attrs: 标签解析出的属性表

    Returns:
        图片消息段；缺少可用内容时为 None
    """
    content = attrs.get("url") or attrs.get("file_id") or attrs.get("fileId", "")
    if content:
        return ImageMessageSegment(data={"content": content})
    return None


DEFAULT_TAG_HANDLERS: dict[str, TagHandler] = {
    "faceType": _parse_face,
    "imageType": _parse_image,
}


def parse_message_tag(
    tag_content: str,
    handlers: dict[str, TagHandler] | None = None,
) -> MessageSegment | None:
    """解析单个标签为统一消息段。

    Args:
        tag_content: 标签内部文本
        handlers: 类型键到解析函数的映射；默认使用内置表

    Returns:
        识别成功时的消息段；无法识别为 None
    """
    handlers = handlers or DEFAULT_TAG_HANDLERS
    attrs = parse_tag_attrs(tag_content)
    for type_key, handler in handlers.items():
        if type_key in attrs:
            return handler(attrs)
    return None


def content_to_messages(
    content: str,
    handlers: dict[str, TagHandler] | None = None,
) -> list[MessageSegment]:
    """把 QQ 正文（纯文本与尖括号标签）拆成统一消息段列表。

    Args:
        content: 平台原始正文字符串
        handlers: 可选自定义标签解析表

    Returns:
        至少包含一段的消息段列表；无法识别的标签跳过
    """
    result: list[MessageSegment] = []
    tag_pattern = re.compile(r"<([^>]+)>")
    last_end = 0

    for m in tag_pattern.finditer(content):
        if m.start() > last_end:
            text = content[last_end : m.start()]
            if text:
                result.append(TextMessageSegment(data={"text": text}))

        seg = parse_message_tag(m.group(1), handlers)
        if seg is not None:
            result.append(seg)

        last_end = m.end()

    if last_end < len(content):
        text = content[last_end:]
        if text:
            result.append(TextMessageSegment(data={"text": text}))

    return result if result else [TextMessageSegment(data={"text": ""})]


def segment_to_qq_tag(seg: MessageSegment) -> str:
    """把单段转回 QQ 发送侧字符串片段。

    Args:
        seg: 统一消息段

    Returns:
        文本段为原文；其它类型暂返回空串
    """
    if seg.type == "text":
        return seg.data.text
    return ""


def messages_to_content(messages: list[MessageSegment]) -> str:
    """把统一消息段列表拼成 QQ 平台正文。

    Args:
        messages: 待发送的消息段列表

    Returns:
        平台可接受的正文字符串
    """
    content = ""
    for message in messages:
        content += segment_to_qq_tag(message)
    return content
