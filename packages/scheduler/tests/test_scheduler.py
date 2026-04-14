from __future__ import annotations

import asyncio
import unittest
from datetime import datetime
from pydantic import ValidationError

from scheduler import At, Every


class EveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_every_immediate_max_runs_stops_scheduler(self) -> None:
        runs: list[int] = []

        sch = Every(seconds=0.01, immediate=True, max_runs=2)
        sch.add(lambda: runs.append(1))

        await asyncio.wait_for(sch.run(), timeout=5.0)

        self.assertEqual(len(runs), 2)

    async def test_every_decorator_registers_handler(self) -> None:
        runs: list[int] = []

        sch = Every(seconds=0.01, immediate=True, max_runs=1)

        @sch
        def tick() -> None:
            runs.append(1)

        await asyncio.wait_for(sch.run(), timeout=5.0)

        self.assertEqual(runs, [1])

    async def test_async_handler(self) -> None:
        runs: list[int] = []

        sch = Every(seconds=0.01, immediate=True, max_runs=1)

        async def tick() -> None:
            runs.append(1)

        sch.add(tick)
        await asyncio.wait_for(sch.run(), timeout=5.0)

        self.assertEqual(runs, [1])

    async def test_stop(self) -> None:
        runs: list[int] = []
        sch = Every(seconds=0.01, immediate=True)

        sch.add(lambda: runs.append(1))

        await sch.start()
        await asyncio.sleep(0.25)
        await sch.stop()
        await sch.wait()

        self.assertGreaterEqual(len(runs), 1)

    async def test_wait_without_start_raises(self) -> None:
        sch = Every(seconds=1)
        with self.assertRaises(RuntimeError) as ctx:
            await sch.wait()
        self.assertIn("not been started", str(ctx.exception).lower())

    def test_every_zero_period_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            Every()

    def test_max_runs_invalid(self) -> None:
        with self.assertRaises(ValidationError):
            Every(seconds=1, max_runs=0)

    def test_forbid_unknown_fields(self) -> None:
        with self.assertRaises(ValidationError):
            Every(seconds=1, not_a_field=True)  # type: ignore[call-arg]


class AtNextTargetTests(unittest.TestCase):
    def test_same_day_later(self) -> None:
        sch = At(hour=15, minute=30, second=0)
        now = datetime(2025, 6, 1, 10, 0, 0)
        self.assertEqual(
            sch._next_target(now),
            datetime(2025, 6, 1, 15, 30, 0),
        )

    def test_rolls_to_next_calendar_day(self) -> None:
        sch = At(hour=9, minute=0, second=0)
        now = datetime(2025, 6, 1, 10, 0, 0)
        self.assertEqual(
            sch._next_target(now),
            datetime(2025, 6, 2, 9, 0, 0),
        )

    def test_weekday_same_day_still_future(self) -> None:
        sch = At(hour=12, minute=0, second=0, weekday=0)
        now = datetime(2025, 1, 6, 8, 0, 0)
        self.assertEqual(now.weekday(), 0)
        self.assertEqual(
            sch._next_target(now),
            datetime(2025, 1, 6, 12, 0, 0),
        )

    def test_weekday_same_day_already_passed(self) -> None:
        sch = At(hour=10, minute=0, second=0, weekday=0)
        now = datetime(2025, 1, 6, 15, 0, 0)
        self.assertEqual(
            sch._next_target(now),
            datetime(2025, 1, 13, 10, 0, 0),
        )

    def test_day_one_should_not_skip_to_day_after_tomorrow_when_last_fire_is_late(self) -> None:
        sch = At(hour=8, minute=0, second=0, day=1)
        sch._run_count = 1
        sch._last_fire_at = datetime(2025, 6, 1, 23, 0, 0)
        self.assertEqual(
            sch._next_target(sch._last_fire_at),
            datetime(2025, 6, 2, 8, 0, 0),
        )


if __name__ == "__main__":
    unittest.main()
