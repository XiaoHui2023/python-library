from __future__ import annotations

from datetime import datetime, timezone

from ai_agent.memory.compression_work import (
    CompressImportantResult,
    CompressImportantWork,
    CompressLongResult,
    CompressLongWork,
    CompressionResult,
    CompressionWork,
    DateToLongResult,
    DateToLongWork,
    ShortToDateResult,
    ShortToDateWork,
)
from ai_agent.memory.config import MemoryConfig
from ai_agent.memory.models import (
    DateMemoryDay,
    ImportantMemoryEntry,
    MemorySnapshot,
)
from ai_agent.memory.worker import MemoryTask, MemoryTaskKind


def prepare_work(
    snapshot: MemorySnapshot,
    task: MemoryTask,
    *,
    config: MemoryConfig,
) -> CompressionWork | None:
    if task.kind == MemoryTaskKind.SHORT_TO_DATE:
        batch_size = int(task.payload.get("batch_size", 1))
        if not snapshot.short_term:
            return None
        take = min(batch_size, len(snapshot.short_term))
        batch = tuple(
            m.model_copy(deep=True) for m in snapshot.short_term[:take]
        )
        return ShortToDateWork(batch=batch, batch_size=take)
    if task.kind == MemoryTaskKind.DATE_TO_LONG:
        day_label = str(task.payload["day"])
        day = _find_day(snapshot, day_label)
        if day is None or not day.entries:
            return None
        entries = tuple(e.model_copy(deep=True) for e in day.entries)
        return DateToLongWork(day_label=day_label, entries=entries)
    if task.kind == MemoryTaskKind.COMPRESS_LONG:
        if len(snapshot.long_term) <= config.long_term_max_chunks:
            return None
        chunks = tuple(c.model_copy(deep=True) for c in snapshot.long_term)
        return CompressLongWork(chunks=chunks)
    if task.kind == MemoryTaskKind.COMPRESS_IMPORTANT:
        if len(snapshot.important) <= config.important_max_entries:
            return None
        entries = tuple(e.model_copy(deep=True) for e in snapshot.important)
        return CompressImportantWork(entries=entries)
    return None


def apply_result(
    snapshot: MemorySnapshot,
    task: MemoryTask,
    work: CompressionWork,
    result: CompressionResult,
    *,
    config: MemoryConfig,
) -> list[MemoryTask]:
    if task.kind == MemoryTaskKind.SHORT_TO_DATE:
        return _apply_short_to_date(snapshot, work, result, config=config)
    if task.kind == MemoryTaskKind.DATE_TO_LONG:
        _apply_date_to_long(snapshot, work, result)
        return []
    if task.kind == MemoryTaskKind.COMPRESS_LONG:
        _apply_compress_long(snapshot, result)
        return []
    if task.kind == MemoryTaskKind.COMPRESS_IMPORTANT:
        _apply_compress_important(snapshot, result)
        return []
    return []


def _apply_short_to_date(
    snapshot: MemorySnapshot,
    work: CompressionWork,
    result: CompressionResult,
    *,
    config: MemoryConfig,
) -> list[MemoryTask]:
    if not isinstance(work, ShortToDateWork) or not isinstance(
        result,
        ShortToDateResult,
    ):
        return []
    remove = min(work.batch_size, len(snapshot.short_term))
    if remove:
        snapshot.short_term = snapshot.short_term[remove:]
    day = _find_or_create_day(snapshot, result.day_label)
    day.entries.extend(result.entries)
    now = datetime.now(timezone.utc)
    for text in result.important_texts:
        snapshot.important.append(
            ImportantMemoryEntry(at=now, content=text, source="short_term"),
        )
    followups: list[MemoryTask] = []
    if day is not None and len(day.entries) > config.date_memory_max_entries_per_day:
        followups.append(
            MemoryTask(MemoryTaskKind.DATE_TO_LONG, {"day": result.day_label}),
        )
    return followups


def _apply_date_to_long(
    snapshot: MemorySnapshot,
    work: CompressionWork,
    result: CompressionResult,
) -> None:
    if not isinstance(work, DateToLongWork) or not isinstance(
        result,
        DateToLongResult,
    ):
        return
    snapshot.long_term.append(result.chunk)
    snapshot.date_days = [d for d in snapshot.date_days if d.date != work.day_label]


def _apply_compress_long(
    snapshot: MemorySnapshot,
    result: CompressionResult,
) -> None:
    if not isinstance(result, CompressLongResult):
        return
    snapshot.long_term = list(result.chunks)


def _apply_compress_important(
    snapshot: MemorySnapshot,
    result: CompressionResult,
) -> None:
    if not isinstance(result, CompressImportantResult):
        return
    snapshot.important = list(result.entries)


def _find_or_create_day(snapshot: MemorySnapshot, day_label: str) -> DateMemoryDay:
    existing = _find_day(snapshot, day_label)
    if existing is not None:
        return existing
    day = DateMemoryDay(date=day_label, entries=[])
    snapshot.date_days.append(day)
    return day


def _find_day(snapshot: MemorySnapshot, day_label: str) -> DateMemoryDay | None:
    for day in snapshot.date_days:
        if day.date == day_label:
            return day
    return None
