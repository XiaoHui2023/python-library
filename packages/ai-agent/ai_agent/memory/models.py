from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


MessageRole = Literal["user", "assistant"]


class MemoryMessage(BaseModel):
    """短期记忆中的单条对话。"""

    model_config = ConfigDict(extra="forbid")

    speaker: str = Field(description="讲述者显示名")
    role: MessageRole = Field(description="OpenAI 角色")
    content: str = Field(description="原文")
    at: datetime = Field(description="发生时刻")


class DateMemoryEntry(BaseModel):
    """日期记忆中的压缩条目。"""

    model_config = ConfigDict(extra="forbid")

    at: datetime = Field(description="原话发生时刻")
    speaker: str = Field(description="讲述者显示名")
    summary: str = Field(description="压缩摘要")


class DateMemoryDay(BaseModel):
    """某一天的日期记忆。"""

    model_config = ConfigDict(extra="forbid")

    date: str = Field(description="YYYY-MM-DD")
    entries: list[DateMemoryEntry] = Field(default_factory=list)


class LongTermChunk(BaseModel):
    """长期记忆块；越久越模糊。"""

    model_config = ConfigDict(extra="forbid")

    created_at: datetime = Field(description="首次写入时刻")
    updated_at: datetime = Field(description="最近更新时刻")
    summary: str = Field(description="模糊化摘要")
    clarity: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="清晰程度，1 为最新，趋近 0 表示已融合",
    )


class ImportantMemoryEntry(BaseModel):
    """需长期保留的事实或偏好。"""

    model_config = ConfigDict(extra="forbid")

    at: datetime = Field(description="记录时刻")
    content: str = Field(description="要记住的内容")
    source: str = Field(default="", description="来源说明，如讲述者或压缩任务")


class MemorySnapshot(BaseModel):
    """单会话记忆快照，对应存储目录根。"""

    model_config = ConfigDict(extra="forbid")

    short_term: list[MemoryMessage] = Field(default_factory=list)
    date_days: list[DateMemoryDay] = Field(default_factory=list)
    long_term: list[LongTermChunk] = Field(default_factory=list)
    important: list[ImportantMemoryEntry] = Field(default_factory=list)
