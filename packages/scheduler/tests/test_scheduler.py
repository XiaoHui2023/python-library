from __future__ import annotations

import unittest

from scheduler import Scheduler
from scheduler.job import Every, Job


class SchedulerTests(unittest.IsolatedAsyncioTestCase):
    def tearDown(self) -> None:
        Job._registry.clear()

    async def test_every_immediate_max_runs_stops_scheduler(self) -> None:
        runs: list[int] = []

        @Every(seconds=0.01, max_runs=2, immediate=True)
        def tick() -> None:
            runs.append(1)

        await Scheduler(interval=0.01).run()

        self.assertEqual(len(runs), 2)


if __name__ == "__main__":
    unittest.main()
