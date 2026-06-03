from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MemoryConfig(BaseModel):
    """记忆系统容量与保留策略。"""

    model_config = ConfigDict(extra="forbid")

    short_term_max_messages: int = Field(
        default=20,
        ge=1,
        description="短期记忆条数上限，超出后最旧的一批转入日期记忆",
    )
    short_term_overflow_batch: int = Field(
        default=5,
        ge=1,
        description="每次从短期弹出的消息条数",
    )
    date_memory_days: int = Field(
        default=7,
        ge=1,
        description="日期记忆保留天数，超出后转入长期记忆",
    )
    date_memory_max_entries_per_day: int = Field(
        default=50,
        ge=1,
        description="单日日期记忆条目上限，超出后触发压缩",
    )
    long_term_max_chunks: int = Field(
        default=30,
        ge=1,
        description="长期记忆块数上限，超出后合并较旧条目",
    )
    important_max_entries: int = Field(
        default=20,
        ge=1,
        description="重要记忆条目上限，超出后压缩并调和矛盾",
    )
