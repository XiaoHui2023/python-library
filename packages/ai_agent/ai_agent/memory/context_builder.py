from __future__ import annotations

from dataclasses import dataclass

from ai_agent.context import ChatMessage
from ai_agent.memory.models import MemorySnapshot


@dataclass
class BuiltMemoryContext:
    """供 Agent 使用的记忆上下文。"""

    system_supplement: str
    messages: list[ChatMessage]


def build_memory_context(snapshot: MemorySnapshot) -> BuiltMemoryContext:
    """
    将四层记忆格式化为系统补充与短期消息列表。

    短期记忆转为带 name 的 ChatMessage，便于模型区分讲述者。
    """
    sections: list[str] = []
    if snapshot.important:
        lines = [f"- {entry.content}" for entry in snapshot.important]
        sections.append("【重要记忆】\n" + "\n".join(lines))
    if snapshot.long_term:
        lines = []
        for chunk in sorted(snapshot.long_term, key=lambda c: c.created_at):
            lines.append(f"- ({chunk.clarity:.1f}) {chunk.summary}")
        sections.append("【长期记忆】\n" + "\n".join(lines))
    if snapshot.date_days:
        day_blocks: list[str] = []
        for day in sorted(snapshot.date_days, key=lambda d: d.date):
            if not day.entries:
                continue
            entry_lines = []
            for entry in day.entries:
                stamp = entry.at.strftime("%H:%M")
                entry_lines.append(f"  {stamp} {entry.speaker}: {entry.summary}")
            day_blocks.append(f"{day.date}\n" + "\n".join(entry_lines))
        if day_blocks:
            sections.append("【日期记忆】\n" + "\n\n".join(day_blocks))
    supplement = ""
    if sections:
        supplement = (
            "以下是与本会话相关的分层记忆；回答时须区分各讲述者，"
            "勿把不同人的话混为同一人。\n\n"
            + "\n\n".join(sections)
        )
    messages: list[ChatMessage] = []
    for msg in snapshot.short_term:
        name = msg.speaker
        messages.append(
            ChatMessage(role=msg.role, content=msg.content, name=name),
        )
    return BuiltMemoryContext(system_supplement=supplement, messages=messages)
