from __future__ import annotations

import asyncio
import unittest

from automation.automation import Automation, _instances
from automation.runtime import start, stop


class AutomationTimingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        _instances.clear()

    def tearDown(self) -> None:
        _instances.clear()

    async def test_timing_loop_exits_on_stop(self) -> None:
        ticks: list[int] = []

        class _TickAutomation(Automation):
            interval: float = 0.05

            async def on_tick(self) -> None:
                ticks.append(1)

        _TickAutomation(name="tick")
        loop_task = asyncio.create_task(start())
        await asyncio.sleep(0.13)
        await stop()
        await loop_task
        self.assertGreater(len(ticks), 0)
        self.assertLess(len(ticks), 50)

    async def test_empty_on_tick_still_waits_interval(self) -> None:
        automation = Automation(name="idle", interval=0.05)
        loop_task = asyncio.create_task(start())
        await asyncio.sleep(0.12)
        await stop()
        await loop_task
        self.assertIsNotNone(automation.ctx)
        self.assertFalse(automation.ctx.is_running)


if __name__ == "__main__":
    unittest.main()
