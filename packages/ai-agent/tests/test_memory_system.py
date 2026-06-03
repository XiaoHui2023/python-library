from __future__ import annotations

import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone

from ai_agent.memory import MemoryConfig, MemorySystem
from ai_agent.memory.compressor import RuleMemoryCompressor
from ai_agent.memory.models import MemoryMessage
from ai_agent.memory.context_builder import build_memory_context
from ai_agent.memory.models import (
    DateMemoryDay,
    DateMemoryEntry,
    ImportantMemoryEntry,
    LongTermChunk,
    MemoryMessage,
    MemorySnapshot,
)
from ai_agent.memory.store import MemoryStore


class TestMemoryStore(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._root = __import__("pathlib").Path(self._tmp.name)
        self._store = MemoryStore(self._root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_round_trip(self) -> None:
        now = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)
        self._store.save_short_term(
            [
                MemoryMessage(
                    speaker="Alice",
                    role="user",
                    content="你好",
                    at=now,
                ),
            ],
        )
        self._store.save_date_day(
            DateMemoryDay(
                date="2026-06-02",
                entries=[
                    DateMemoryEntry(
                        at=now,
                        speaker="Alice",
                        summary="打招呼",
                    ),
                ],
            ),
        )
        loaded = self._store.load()
        self.assertEqual(len(loaded.short_term), 1)
        self.assertEqual(loaded.short_term[0].speaker, "Alice")
        self.assertEqual(len(loaded.date_days), 1)
        self.assertEqual(loaded.date_days[0].entries[0].summary, "打招呼")

    def test_prune_date_files(self) -> None:
        self._store.save_date_day(
            DateMemoryDay(date="2026-06-01", entries=[]),
        )
        self._store.save_date_day(
            DateMemoryDay(date="2026-06-02", entries=[]),
        )
        self._store.prune_date_files({"2026-06-02"})
        remaining = list(self._store.root.joinpath("date").glob("*.json"))
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].stem, "2026-06-02")


class TestMemoryContext(unittest.TestCase):
    def test_speaker_names_on_messages(self) -> None:
        now = datetime(2026, 6, 2, tzinfo=timezone.utc)
        snap = MemorySnapshot(
            short_term=[
                MemoryMessage(
                    speaker="Bob",
                    role="user",
                    content="帮我查天气",
                    at=now,
                ),
                MemoryMessage(
                    speaker="assistant",
                    role="assistant",
                    content="好的",
                    at=now,
                ),
            ],
            important=[
                ImportantMemoryEntry(
                    at=now,
                    content="Bob 住上海",
                    source="explicit",
                ),
            ],
            long_term=[
                LongTermChunk(
                    created_at=now,
                    updated_at=now,
                    summary="曾讨论过出行",
                    clarity=0.8,
                ),
            ],
            date_days=[
                DateMemoryDay(
                    date="2026-06-01",
                    entries=[
                        DateMemoryEntry(
                            at=now,
                            speaker="Carol",
                            summary="提了项目 deadline",
                        ),
                    ],
                ),
            ],
        )
        ctx = build_memory_context(snap)
        self.assertIn("Bob 住上海", ctx.system_supplement)
        self.assertIn("Carol", ctx.system_supplement)
        self.assertEqual(len(ctx.messages), 2)
        self.assertEqual(ctx.messages[0].name, "Bob")
        self.assertEqual(ctx.messages[0].role, "user")
        api = ctx.messages[0].to_api()
        self.assertEqual(api["name"], "Bob")


class TestMemorySystem(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._root = __import__("pathlib").Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _make_system(self, **kwargs) -> MemorySystem:
        defaults = {
            "storage_dir": self._root,
            "api_key": "k",
            "model": "m",
            "base_url": "https://example.invalid/v1",
            "use_llm_compressor": False,
            "compressor": RuleMemoryCompressor(),
        }
        defaults.update(kwargs)
        return MemorySystem(**defaults)

    def test_append_and_build_context(self) -> None:
        mem = self._make_system()
        try:
            mem.append(speaker="Alice", role="user", content="我叫 Alice")
            system, messages = mem.context_for_agent(system_prompt="你是助手")
            self.assertIn("你是助手", system)
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0].name, "Alice")
        finally:
            mem.shutdown()

    def test_short_term_overflow_moves_to_date(self) -> None:
        cfg = MemoryConfig(
            short_term_max_messages=3,
            short_term_overflow_batch=2,
        )
        mem = self._make_system(config=cfg)
        try:
            for i in range(4):
                mem.append(
                    speaker=f"U{i}",
                    role="user",
                    content=f"msg-{i}",
                )
            mem.flush(timeout=10.0)
            snap = MemoryStore(self._root).load()
            self.assertLessEqual(len(snap.short_term), 3)
            self.assertTrue(snap.date_days or snap.long_term)
        finally:
            mem.shutdown()

    def test_remember_important(self) -> None:
        mem = self._make_system()
        try:
            mem.remember("用户偏好深色主题")
            ctx = mem.build_context()
            self.assertIn("深色主题", ctx.system_supplement)
        finally:
            mem.shutdown()

    def test_agent_read_not_blocked_during_compression(self) -> None:
        gate = threading.Event()

        class SlowCompressor(RuleMemoryCompressor):
            async def compress_to_date_entries(self, messages: list[MemoryMessage]):
                gate.wait(timeout=5.0)
                return await super().compress_to_date_entries(messages)

        cfg = MemoryConfig(
            short_term_max_messages=2,
            short_term_overflow_batch=1,
        )
        mem = self._make_system(config=cfg, compressor=SlowCompressor())
        try:
            mem.append(speaker="A", role="user", content="one")
            mem.append(speaker="A", role="user", content="two")
            mem.append(speaker="A", role="user", content="three")
            time.sleep(0.05)
            start = time.monotonic()
            mem.append(speaker="B", role="user", content="during")
            ctx = mem.build_context()
            elapsed = time.monotonic() - start
            self.assertLess(elapsed, 0.5)
            self.assertIn("during", [m.content for m in ctx.messages])
            gate.set()
            mem.flush(timeout=10.0)
        finally:
            mem.shutdown()

    def test_reload_from_disk(self) -> None:
        mem = self._make_system()
        try:
            mem.append(speaker="Tom", role="user", content="持久测试")
            mem.shutdown()
        finally:
            pass
        mem2 = self._make_system()
        try:
            snap = MemoryStore(self._root).load()
            self.assertEqual(len(snap.short_term), 1)
            self.assertEqual(snap.short_term[0].speaker, "Tom")
        finally:
            mem2.shutdown()


if __name__ == "__main__":
    unittest.main()
