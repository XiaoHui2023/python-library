from __future__ import annotations

import json
from pathlib import Path

from ai_agent.context import ChatMessage

_CONVERSATION_FILE = "conversation.json"


def conversation_path(session_root: Path) -> Path:
    """会话根目录下的对话持久化文件路径。"""
    return session_root / _CONVERSATION_FILE


def load_conversation(session_root: Path) -> list[ChatMessage]:
    """
    从磁盘读取对话历史。

    Args:
        session_root: 会话工作区根

    Returns:
        无文件或解析失败时返回空列表
    """
    path = conversation_path(session_root)
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(raw, list):
        return []
    messages: list[ChatMessage] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role not in ("system", "user", "assistant", "tool"):
            continue
        if not isinstance(content, str):
            continue
        name = item.get("name")
        if name is not None and not isinstance(name, str):
            name = None
        messages.append(
            ChatMessage(
                role=role,
                content=content,
                name=name,
            ),
        )
    return messages


def save_conversation(session_root: Path, messages: list[ChatMessage]) -> None:
    """
    将会话对话历史写入磁盘。

    Args:
        session_root: 会话工作区根
        messages: 待持久化的消息列表
    """
    session_root.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "role": m.role,
            "content": m.content,
            **({"name": m.name} if m.name else {}),
        }
        for m in messages
    ]
    conversation_path(session_root).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def clear_conversation(session_root: Path) -> None:
    """删除会话对话持久化文件（若存在）。"""
    path = conversation_path(session_root)
    if path.is_file():
        path.unlink()
