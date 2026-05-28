from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass
from typing import Any

from automation.automation import Automation, _instances
from automation.context import Context
from automation.runtime import run, start, stop


class _Ctx(Context):
    pass


_gate_ran = False
_slow_runs = 0


@dataclass
class _Packet:
    value: int


class _Gate(Automation):
    async def should_run(self) -> bool:
        return False


class CoreFlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        global _gate_ran, _slow_runs
        self.ctx = _Ctx()
        _gate_ran = False
        _slow_runs = 0
        _instances.clear()

    async def test_run_respects_should_run(self) -> None:
        obj = _Gate(name="gate", ctx=self.ctx)

        @obj
        async def mark_ran(_payload: Any) -> None:
            global _gate_ran
            _gate_ran = True

        await obj.run(None)
        self.assertFalse(_gate_ran)

    async def test_automation_register_fires(self) -> None:
        automation = Automation(name="ev", ctx=self.ctx)
        hits: list[Any] = []

        @automation.register
        async def record_payload(payload: Any) -> None:
            hits.append(payload)

        await automation.run({"x": 1})
        self.assertEqual(hits, [{"x": 1}])

    async def test_automation_payload_type_reaches_handler(self) -> None:
        class _PacketAutomation(Automation[_Packet]):
            pass

        automation = _PacketAutomation(name="typed", ctx=self.ctx)
        hits: list[int] = []

        @automation.register
        async def record_packet(payload: _Packet) -> None:
            hits.append(payload.value)

        await automation.run(_Packet(value=7))
        self.assertEqual(hits, [7])

    async def test_automation_skip_mode_skips_when_busy(self) -> None:
        automation = Automation(name="ev", ctx=self.ctx, mode="skip")

        @automation
        async def run_slow(_payload: Any) -> None:
            global _slow_runs
            _slow_runs += 1
            await asyncio.sleep(0.05)

        await asyncio.gather(automation.run(None), automation.run(None))
        self.assertEqual(_slow_runs, 1)

    async def test_automation_handlers_run_in_parallel(self) -> None:
        automation = Automation(name="ev", ctx=self.ctx)
        hits: list[str] = []

        @automation
        async def slow(_payload: Any) -> None:
            await asyncio.sleep(0.05)
            hits.append("slow")

        @automation
        async def fast(_payload: Any) -> None:
            hits.append("fast")

        await automation.run(None)
        self.assertEqual(hits, ["fast", "slow"])

    async def test_automation_handler_error_does_not_block_others(self) -> None:
        automation = Automation(name="ev", ctx=self.ctx)
        hits: list[str] = []

        @automation
        async def fail(_payload: Any) -> None:
            raise RuntimeError("boom")

        @automation
        async def ok(_payload: Any) -> None:
            hits.append("ok")

        with self.assertLogs("automation.automation", level="ERROR"):
            await automation.run(None)
        self.assertEqual(hits, ["ok"])

    async def test_runtime_start_calls_on_init_then_on_build(self) -> None:
        calls: list[str] = []

        class _BuildAutomation(Automation):
            async def on_init(self) -> None:
                calls.append("init:start")
                await super().on_init()
                calls.append("init:end")

            async def on_build(self) -> None:
                calls.append("build")

        _BuildAutomation(name="ev")
        loop_task = asyncio.create_task(run())
        await asyncio.sleep(0)
        await stop()
        await loop_task
        self.assertEqual(calls, ["init:start", "build", "init:end"])


if __name__ == "__main__":
    unittest.main()
