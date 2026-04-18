"""FSChangeOnce 一次性阻塞等待测试。"""

from __future__ import annotations

import asyncio
import tempfile
import threading
import time
import unittest
from pathlib import Path

from fs_change_hook.once import FSChangeOnce, OnceWatchEnd


class TestFSChangeOnce(unittest.TestCase):
    def test_wait_returns_changed_when_file_touched(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "w.txt"
            p.write_text("0", encoding="utf-8")
            once = FSChangeOnce([p])

            def touch_later() -> None:
                time.sleep(0.25)
                p.write_text("1", encoding="utf-8")

            threading.Thread(target=touch_later, daemon=True).start()
            r = once.wait(timeout=5.0)
            self.assertEqual(r, OnceWatchEnd.CHANGED)
            self.assertEqual(once.last_end, OnceWatchEnd.CHANGED)

    def test_wait_returns_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "w.txt"
            p.write_text("0", encoding="utf-8")
            once = FSChangeOnce([p])
            r = once.wait(timeout=0.15)
            self.assertEqual(r, OnceWatchEnd.TIMEOUT)
            self.assertEqual(once.last_end, OnceWatchEnd.TIMEOUT)

    def test_wait_async_changed(self) -> None:
        async def run() -> None:
            with tempfile.TemporaryDirectory() as td:
                p = Path(td) / "w.txt"
                p.write_text("0", encoding="utf-8")
                once = FSChangeOnce([p])

                async def touch_later() -> None:
                    await asyncio.sleep(0.25)
                    p.write_text("1", encoding="utf-8")

                t = asyncio.create_task(touch_later())
                r = await once.wait_async(timeout=5.0)
                await t
                self.assertEqual(r, OnceWatchEnd.CHANGED)

        asyncio.run(run())

    def test_wait_async_timeout(self) -> None:
        async def run() -> None:
            with tempfile.TemporaryDirectory() as td:
                p = Path(td) / "w.txt"
                p.write_text("0", encoding="utf-8")
                once = FSChangeOnce([p])
                r = await once.wait_async(timeout=0.12)
                self.assertEqual(r, OnceWatchEnd.TIMEOUT)

        asyncio.run(run())

    def test_wait_aborts_when_should_abort_true(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "w.txt"
            p.write_text("0", encoding="utf-8")
            once = FSChangeOnce([p])
            stop = threading.Event()

            def flip_abort() -> None:
                time.sleep(0.2)
                stop.set()

            threading.Thread(target=flip_abort, daemon=True).start()
            r = once.wait(
                timeout=5.0,
                poll_interval=0.05,
                should_abort=stop.is_set,
            )
            self.assertEqual(r, OnceWatchEnd.ABORTED)


if __name__ == "__main__":
    unittest.main()
