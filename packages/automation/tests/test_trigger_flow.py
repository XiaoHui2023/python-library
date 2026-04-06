import asyncio
import unittest
from typing import ClassVar

import automation  # noqa: F401

from automation.builder import build_all
from automation.core.entity import Entity
from automation.core.event import Event
from automation.core.trigger import Trigger


class PressEvent(Event):
    _type: ClassVar[str] = "press"


class FlowTrigger(Trigger):
    _type: ClassVar[str] = "flow"


class TriggerFlowTests(unittest.TestCase):
    def test_fire_runs_action_when_condition_true(self) -> None:
        log: list[str] = []

        class LampEntityWithLog(Entity):
            _type: ClassVar[str] = "lamp_log"
            on: bool = True

            def record(self) -> None:
                log.append("done")

        config = {
            "entities": {"lamp": {"type": "lamp_log", "on": True}},
            "events": {"e1": {"type": "press"}},
            "conditions": {
                "c1": {"type": "expression", "expr": "{lamp.on}"},
            },
            "actions": {
                "a1": {
                    "type": "call_entity_method",
                    "entity": "lamp",
                    "method": "record",
                    "args": {},
                },
            },
            "triggers": {
                "t1": {
                    "type": "flow",
                    "event": "e1",
                    "conditions": ["c1"],
                    "actions": ["a1"],
                },
            },
        }

        ctx = build_all(config)

        async def run() -> None:
            await ctx.events["e1"].fire()

        asyncio.run(run())
        self.assertEqual(log, ["done"])

    def test_fire_skips_action_when_condition_false(self) -> None:
        log: list[str] = []

        class LampEntityWithLog(Entity):
            _type: ClassVar[str] = "lamp_log2"
            on: bool = False

            def record(self) -> None:
                log.append("done")

        config = {
            "entities": {"lamp": {"type": "lamp_log2", "on": False}},
            "events": {"e1": {"type": "press"}},
            "conditions": {
                "c1": {"type": "expression", "expr": "{lamp.on}"},
            },
            "actions": {
                "a1": {
                    "type": "call_entity_method",
                    "entity": "lamp",
                    "method": "record",
                    "args": {},
                },
            },
            "triggers": {
                "t1": {
                    "type": "flow",
                    "event": "e1",
                    "conditions": ["c1"],
                    "actions": ["a1"],
                },
            },
        }

        ctx = build_all(config)

        async def run() -> None:
            await ctx.events["e1"].fire()

        asyncio.run(run())
        self.assertEqual(log, [])


if __name__ == "__main__":
    unittest.main()
