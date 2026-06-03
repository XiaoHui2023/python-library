from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from ai_agent.memory.models import (
    DateMemoryEntry,
    DateMemoryDay,
    ImportantMemoryEntry,
    LongTermChunk,
    MemoryMessage,
)


@dataclass(frozen=True)
class ShortToDateWork:
    batch: tuple[MemoryMessage, ...]
    batch_size: int


@dataclass(frozen=True)
class ShortToDateResult:
    entries: tuple[DateMemoryEntry, ...]
    important_texts: tuple[str, ...]
    day_label: str


@dataclass(frozen=True)
class DateToLongWork:
    day_label: str
    entries: tuple[DateMemoryEntry, ...]


@dataclass(frozen=True)
class DateToLongResult:
    chunk: LongTermChunk


@dataclass(frozen=True)
class CompressLongWork:
    chunks: tuple[LongTermChunk, ...]


@dataclass(frozen=True)
class CompressLongResult:
    chunks: tuple[LongTermChunk, ...]


@dataclass(frozen=True)
class CompressImportantWork:
    entries: tuple[ImportantMemoryEntry, ...]


@dataclass(frozen=True)
class CompressImportantResult:
    entries: tuple[ImportantMemoryEntry, ...]


CompressionWork = Union[
    ShortToDateWork,
    DateToLongWork,
    CompressLongWork,
    CompressImportantWork,
]

CompressionResult = Union[
    ShortToDateResult,
    DateToLongResult,
    CompressLongResult,
    CompressImportantResult,
]
