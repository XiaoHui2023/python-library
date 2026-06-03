from __future__ import annotations

import enum
import queue
import threading
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Callable

from ai_agent.memory.compression_work import (
    CompressImportantWork,
    CompressLongWork,
    CompressionResult,
    CompressionWork,
    CompressImportantResult,
    CompressLongResult,
    DateToLongResult,
    DateToLongWork,
    ShortToDateResult,
    ShortToDateWork,
)
from ai_agent.memory.compressor import MemoryCompressor
from ai_agent.memory.config import MemoryConfig
class MemoryTaskKind(str, enum.Enum):
    SHORT_TO_DATE = "short_to_date"
    DATE_TO_LONG = "date_to_long"
    COMPRESS_LONG = "compress_long"
    COMPRESS_IMPORTANT = "compress_important"


@dataclass
class MemoryTask:
    kind: MemoryTaskKind
    payload: dict


class MemoryWorker:
    """
    独立线程上的记忆维护：弹出短期、归档日期、压缩长期与重要记忆。

    压缩在锁外执行；提交结果时由调用方短暂持锁合并并发布 Agent 视图。
    """

    def __init__(
        self,
        *,
        config: MemoryConfig,
        compressor_factory: Callable[[], MemoryCompressor],
        prepare: Callable[[MemoryTask], CompressionWork | None],
        commit: Callable[[MemoryTask, CompressionWork, CompressionResult], None],
    ) -> None:
        self._config = config
        self._compressor_factory = compressor_factory
        self._prepare = prepare
        self._commit = commit
        self._queue: queue.Queue[MemoryTask | None] = queue.Queue()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._thread_main,
            name="memory-worker",
            daemon=True,
        )
        self._thread.start()

    def stop(self, *, join: bool = True, timeout: float | None = 5.0) -> None:
        self._queue.put(None)
        if join and self._thread is not None:
            self._thread.join(timeout=timeout)

    def enqueue(self, task: MemoryTask) -> None:
        self._queue.put(task)

    def drain(self, *, timeout: float = 30.0) -> None:
        """等待队列中已有任务处理完毕（不含后续新任务）。"""
        done = threading.Event()
        sentinel = MemoryTask(
            MemoryTaskKind.COMPRESS_IMPORTANT,
            {"drain": True, "done": done},
        )
        self._queue.put(sentinel)
        if not done.wait(timeout=timeout):
            raise TimeoutError("记忆压缩队列等待超时")

    def _thread_main(self) -> None:
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run_loop())
        finally:
            loop.close()

    async def _run_loop(self) -> None:
        compressor = self._compressor_factory()
        while True:
            task = await _queue_get_async(self._queue)
            if task is None:
                return
            if task.payload.get("drain"):
                event = task.payload.get("done")
                if isinstance(event, threading.Event):
                    event.set()
                continue
            work = self._prepare(task)
            if work is None:
                continue
            result = await _process_task(compressor, task, work, self._config)
            if result is None:
                continue
            self._commit(task, work, result)

    @property
    def config(self) -> MemoryConfig:
        return self._config


async def _process_task(
    compressor: MemoryCompressor,
    task: MemoryTask,
    work: CompressionWork,
    config: MemoryConfig,
) -> CompressionResult | None:
    if task.kind == MemoryTaskKind.SHORT_TO_DATE:
        return await _process_short_to_date(compressor, work)
    if task.kind == MemoryTaskKind.DATE_TO_LONG:
        return await _process_date_to_long(compressor, work)
    if task.kind == MemoryTaskKind.COMPRESS_LONG:
        return await _process_compress_long(compressor, work, config)
    if task.kind == MemoryTaskKind.COMPRESS_IMPORTANT:
        return await _process_compress_important(compressor, work, config)
    return None


async def _process_short_to_date(
    compressor: MemoryCompressor,
    work: CompressionWork,
) -> ShortToDateResult | None:
    if not isinstance(work, ShortToDateWork) or not work.batch:
        return None
    batch = list(work.batch)
    entries, important_texts = await compressor.compress_to_date_entries(batch)
    day_label = _day_label(batch[0].at)
    return ShortToDateResult(
        entries=tuple(entries),
        important_texts=tuple(important_texts),
        day_label=day_label,
    )


async def _process_date_to_long(
    compressor: MemoryCompressor,
    work: CompressionWork,
) -> DateToLongResult | None:
    if not isinstance(work, DateToLongWork):
        return None
    chunk = await compressor.merge_date_to_long_term(
        work.day_label,
        list(work.entries),
    )
    return DateToLongResult(chunk=chunk)


async def _process_compress_long(
    compressor: MemoryCompressor,
    work: CompressionWork,
    config: MemoryConfig,
) -> CompressLongResult | None:
    if not isinstance(work, CompressLongWork):
        return None
    if len(work.chunks) <= config.long_term_max_chunks:
        return None
    merged = await compressor.merge_long_term_chunks(list(work.chunks))
    return CompressLongResult(chunks=tuple(merged))


async def _process_compress_important(
    compressor: MemoryCompressor,
    work: CompressionWork,
    config: MemoryConfig,
) -> CompressImportantResult | None:
    if not isinstance(work, CompressImportantWork):
        return None
    if len(work.entries) <= config.important_max_entries:
        return None
    merged = await compressor.reconcile_important(list(work.entries))
    return CompressImportantResult(entries=tuple(merged))


async def _queue_get_async(q: queue.Queue) -> MemoryTask | None:
    import asyncio

    while True:
        try:
            return q.get_nowait()
        except queue.Empty:
            await asyncio.sleep(0.05)


def _day_label(at: datetime) -> str:
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    return at.astimezone(timezone.utc).date().isoformat()


def expire_old_date_days(
    snapshot,
    *,
    config: MemoryConfig,
    today: date | None = None,
) -> list[str]:
    """返回应归档到长期记忆的过期日期标签。"""
    ref = today or datetime.now(timezone.utc).date()
    cutoff = ref - timedelta(days=config.date_memory_days - 1)
    expired: list[str] = []
    for day in snapshot.date_days:
        try:
            day_date = date.fromisoformat(day.date)
        except ValueError:
            continue
        if day_date < cutoff:
            expired.append(day.date)
    return expired
