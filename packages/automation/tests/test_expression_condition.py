import asyncio
import logging
import unittest
from typing import ClassVar

import automation  # noqa: F401

from automation import loader
from automation.core.entity import Entity
from automation.core.event import Event
from automation.hub import Hub


class ExpressionEvent(Event):
    _type: ClassVar[str] = "expression_event"


class LampEntity(Entity):
    _type: ClassVar[str] = "expression_lamp"
    on: bool = False
    load: float = 0.0
    called: bool = False

    def record(self) -> None:
        self.called = True


class ExpressionConditionTests(unittest.TestCase):
    def test_expression_can_reference_condition_and_entity(self) -> None:
        config = {
            "entities": {
                "lamp": {
                    "type": "expression_lamp",
                    "on": True,
                    "load": 0.4,
                    "called": False,
                },
            },
            "events": {"e1": {"type": "expression_event"}},
            "conditions": {
                "is_on": {"type": "expression", "expr": "{lamp.on}"},
                "can_run": {
                    "type": "expression",
                    "expr": "{is_on} and {lamp.load} < 0.8",
                },
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
                    "event": "e1",
                    "conditions": ["can_run"],
                    "actions": ["a1"],
                },
            },
        }

        async def run() -> Hub:
            hub = Hub()
            await loader.load(hub, config)
            await hub.events["e1"].fire()
            return hub

        hub = asyncio.run(run())
        self.assertTrue(hub.entities["lamp"].called)

    def test_expression_detects_condition_cycle(self) -> None:
        config = {
            "entities": {
                "lamp": {
                    "type": "expression_lamp",
                    "on": True,
                    "load": 0.4,
                    "called": False,
                },
            },
            "events": {"e1": {"type": "expression_event"}},
            "conditions": {
                "c1": {"type": "expression", "expr": "{c2}"},
                "c2": {"type": "expression", "expr": "{c1}"},
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
                    "event": "e1",
                    "conditions": ["c1"],
                    "actions": ["a1"],
                },
            },
        }

        recorded: list[Exception] = []

        def on_error(exc: Exception) -> None:
            recorded.append(exc)

        elog = logging.getLogger("automation.core.event")
        old_level = elog.level
        elog.setLevel(logging.CRITICAL)

        async def run() -> Hub:
            hub = Hub()
            await loader.load(hub, config)
            hub.events["e1"].set_error_handler(on_error)
            await hub.events["e1"].fire()
            return hub

        try:
            hub = asyncio.run(run())
        finally:
            elog.setLevel(old_level)
        self.assertEqual(len(recorded), 1)
        self.assertIn("Circular condition dependency", str(recorded[0]))
        self.assertFalse(hub.entities["lamp"].called)


if __name__ == "__main__":
    unittest.main()
