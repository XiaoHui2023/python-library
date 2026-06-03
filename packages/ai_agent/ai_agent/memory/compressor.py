from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Protocol

from ai_agent.context import ChatMessage, RunContext
from ai_agent.llm import LLMClient, StreamKind
from ai_agent.memory.models import (
    DateMemoryEntry,
    ImportantMemoryEntry,
    LongTermChunk,
    MemoryMessage,
)


class MemoryCompressor(Protocol):
    """记忆压缩接口；默认由语言模型实现，测试可替换。"""

    async def compress_to_date_entries(
        self,
        messages: list[MemoryMessage],
    ) -> tuple[list[DateMemoryEntry], list[str]]:
        """
        将一批短期消息压缩为日期记忆条目，并提取重要事实。

        Returns:
            (日期条目, 重要事实文本列表)
        """

    async def merge_date_to_long_term(
        self,
        day_label: str,
        entries: list[DateMemoryEntry],
    ) -> LongTermChunk:
        """将一整天的日期记忆合并为一块长期记忆。"""

    async def merge_long_term_chunks(
        self,
        chunks: list[LongTermChunk],
    ) -> list[LongTermChunk]:
        """合并较旧的长期记忆块并降低清晰度。"""

    async def reconcile_important(
        self,
        entries: list[ImportantMemoryEntry],
    ) -> list[ImportantMemoryEntry]:
        """压缩重要记忆并调和矛盾。"""


class LLMMemoryCompressor:
    """用语言模型执行各层压缩。"""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def compress_to_date_entries(
        self,
        messages: list[MemoryMessage],
    ) -> tuple[list[DateMemoryEntry], list[str]]:
        if not messages:
            return [], []
        lines = []
        for msg in messages:
            stamp = msg.at.isoformat()
            lines.append(f"[{stamp}] {msg.speaker} ({msg.role}): {msg.content}")
        user_text = "\n".join(lines)
        system = (
            "你是会话记忆整理助手。输入是一批带时间与讲述者的对话原文。"
            "过滤寒暄与重复，保留事实、决定、偏好与待办。"
            "输出 JSON 对象，字段："
            "entries 为数组，每项含 at（ISO8601）、speaker、summary；"
            "important 为字符串数组，列出需长期记住的事实。"
            "只输出 JSON，不要 markdown。"
        )
        raw = await _complete(self._llm, system, user_text)
        data = _parse_json_object(raw)
        entries: list[DateMemoryEntry] = []
        for item in data.get("entries", []):
            if not isinstance(item, dict):
                continue
            summary = str(item.get("summary", "")).strip()
            speaker = str(item.get("speaker", "")).strip() or "unknown"
            at_raw = item.get("at")
            at = _parse_datetime(at_raw, fallback=messages[0].at)
            if summary:
                entries.append(
                    DateMemoryEntry(at=at, speaker=speaker, summary=summary),
                )
        important = [
            str(x).strip()
            for x in data.get("important", [])
            if str(x).strip()
        ]
        if not entries:
            entries = _fallback_date_entries(messages)
        return entries, important

    async def merge_date_to_long_term(
        self,
        day_label: str,
        entries: list[DateMemoryEntry],
    ) -> LongTermChunk:
        if not entries:
            now = datetime.now(timezone.utc)
            return LongTermChunk(
                created_at=now,
                updated_at=now,
                summary=f"{day_label} 无有效记忆",
                clarity=0.6,
            )
        lines = []
        for entry in entries:
            stamp = entry.at.isoformat()
            lines.append(f"[{stamp}] {entry.speaker}: {entry.summary}")
        system = (
            "将一天的日期记忆压缩为一段长期记忆摘要。"
            "保留关键事实但允许适度模糊；输出 JSON："
            '{"summary":"..."}。只输出 JSON。'
        )
        raw = await _complete(self._llm, system, "\n".join(lines))
        data = _parse_json_object(raw)
        summary = str(data.get("summary", "")).strip()
        if not summary:
            summary = _fallback_day_summary(day_label, entries)
        now = datetime.now(timezone.utc)
        return LongTermChunk(
            created_at=now,
            updated_at=now,
            summary=summary,
            clarity=0.75,
        )

    async def merge_long_term_chunks(
        self,
        chunks: list[LongTermChunk],
    ) -> list[LongTermChunk]:
        if len(chunks) <= 1:
            return chunks
        ordered = sorted(chunks, key=lambda c: c.created_at)
        merge_count = max(1, len(ordered) // 3)
        old_batch = ordered[:merge_count]
        rest = ordered[merge_count:]
        lines = []
        for chunk in old_batch:
            lines.append(f"(clarity={chunk.clarity:.2f}) {chunk.summary}")
        system = (
            "将多段较旧的长期记忆融合为更少、更模糊的摘要块。"
            "输出 JSON：chunks 为数组，每项含 summary 与 clarity（0~1，越低越模糊）。"
            "只输出 JSON。"
        )
        raw = await _complete(self._llm, system, "\n".join(lines))
        data = _parse_json_object(raw)
        merged: list[LongTermChunk] = []
        now = datetime.now(timezone.utc)
        for item in data.get("chunks", []):
            if not isinstance(item, dict):
                continue
            summary = str(item.get("summary", "")).strip()
            if not summary:
                continue
            clarity = float(item.get("clarity", 0.4))
            clarity = max(0.0, min(1.0, clarity))
            merged.append(
                LongTermChunk(
                    created_at=old_batch[0].created_at,
                    updated_at=now,
                    summary=summary,
                    clarity=clarity,
                ),
            )
        if not merged:
            merged = [_fallback_merge_chunks(old_batch)]
        return merged + rest

    async def reconcile_important(
        self,
        entries: list[ImportantMemoryEntry],
    ) -> list[ImportantMemoryEntry]:
        if not entries:
            return []
        lines = []
        for entry in entries:
            stamp = entry.at.isoformat()
            src = entry.source or "unknown"
            lines.append(f"[{stamp}] ({src}) {entry.content}")
        system = (
            "整理重要记忆列表：合并重复、调和矛盾（以最新或更可信者为准并说明取舍）。"
            "输出 JSON：entries 为数组，每项含 content 与 source。"
            "只输出 JSON。"
        )
        raw = await _complete(self._llm, system, "\n".join(lines))
        data = _parse_json_object(raw)
        now = datetime.now(timezone.utc)
        out: list[ImportantMemoryEntry] = []
        for item in data.get("entries", []):
            if not isinstance(item, dict):
                continue
            content = str(item.get("content", "")).strip()
            if not content:
                continue
            source = str(item.get("source", "")).strip()
            out.append(
                ImportantMemoryEntry(at=now, content=content, source=source),
            )
        if not out:
            out = entries[-max(1, len(entries) // 2):]
        return out


class RuleMemoryCompressor:
    """无语言模型时的规则压缩，供测试或离线降级。"""

    async def compress_to_date_entries(
        self,
        messages: list[MemoryMessage],
    ) -> tuple[list[DateMemoryEntry], list[str]]:
        entries = _fallback_date_entries(messages)
        important: list[str] = []
        for msg in messages:
            text = msg.content.strip()
            if len(text) >= 40 and "?" not in text[:8]:
                important.append(f"{msg.speaker}: {text[:120]}")
        return entries, important[:3]

    async def merge_date_to_long_term(
        self,
        day_label: str,
        entries: list[DateMemoryEntry],
    ) -> LongTermChunk:
        now = datetime.now(timezone.utc)
        summary = _fallback_day_summary(day_label, entries)
        return LongTermChunk(
            created_at=now,
            updated_at=now,
            summary=summary,
            clarity=0.7,
        )

    async def merge_long_term_chunks(
        self,
        chunks: list[LongTermChunk],
    ) -> list[LongTermChunk]:
        if len(chunks) <= 1:
            return chunks
        ordered = sorted(chunks, key=lambda c: c.created_at)
        merge_count = max(1, len(ordered) // 3)
        merged = _fallback_merge_chunks(ordered[:merge_count])
        return [merged] + ordered[merge_count:]

    async def reconcile_important(
        self,
        entries: list[ImportantMemoryEntry],
    ) -> list[ImportantMemoryEntry]:
        seen: set[str] = set()
        out: list[ImportantMemoryEntry] = []
        for entry in reversed(entries):
            key = entry.content.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(entry)
        out.reverse()
        return out[: max(1, len(entries) // 2 + 1)]


async def _complete(llm: LLMClient, system: str, user: str) -> str:
    run = RunContext(
        system_prompt=system,
        messages=[ChatMessage(role="user", content=user)],
    )
    parts: list[str] = []
    async for chunk in llm.stream(run):
        if chunk.kind == StreamKind.TEXT:
            parts.append(chunk.delta)
    return "".join(parts).strip()


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if not text:
        return {}
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _parse_datetime(value: Any, *, fallback: datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return fallback


def _fallback_date_entries(messages: list[MemoryMessage]) -> list[DateMemoryEntry]:
    entries: list[DateMemoryEntry] = []
    for msg in messages:
        text = msg.content.strip()
        if not text:
            continue
        summary = text if len(text) <= 160 else text[:157] + "..."
        entries.append(
            DateMemoryEntry(at=msg.at, speaker=msg.speaker, summary=summary),
        )
    return entries


def _fallback_day_summary(day_label: str, entries: list[DateMemoryEntry]) -> str:
    if not entries:
        return f"{day_label} 无记录"
    parts = [f"{e.speaker}: {e.summary}" for e in entries[:8]]
    tail = f" 等共 {len(entries)} 条" if len(entries) > 8 else ""
    return f"{day_label} — " + "；".join(parts) + tail


def _fallback_merge_chunks(chunks: list[LongTermChunk]) -> LongTermChunk:
    now = datetime.now(timezone.utc)
    texts = [c.summary for c in chunks if c.summary.strip()]
    joined = " / ".join(texts[:5])
    if len(texts) > 5:
        joined += f" …(+{len(texts) - 5})"
    clarity_vals = [c.clarity for c in chunks]
    clarity = min(clarity_vals) * 0.7 if clarity_vals else 0.35
    return LongTermChunk(
        created_at=chunks[0].created_at,
        updated_at=now,
        summary=joined,
        clarity=max(0.1, clarity),
    )
