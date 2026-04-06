import asyncio
import unittest
from typing import ClassVar

import automation  # noqa: F401

from automation.builder import build_all
from automation.core.entity import Entity
from automation.core.event import Event
from automation.core.trigger import Trigger


class ExpressionEvent(Event):
    _type: ClassVar[str] = "expression_event"


class ExpressionTrigger(Trigger):
    _type: ClassVar[str] = "expression_trigger"


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
                "lamp": {"type": "expression_lamp", "on": True, "load": 0.4, "called": False},
            },
            "events": {"e1": {"type": "expression_event"}},
            "conditions": {
                "is_on": {"type": "expression", "expr": "{lamp.on}"},
                "can_run": {"type": "expression", "expr": "{is_on} and {lamp.load} < 0.8"},
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
                    "type": "expression_trigger",
                    "event": "e1",
                    "conditions": ["can_run"],
                    "actions": ["a1"],
                },
            },
        }

        ctx = build_all(config)

        async def run() -> None:
            await ctx.events["e1"].fire()

        asyncio.run(run())
        self.assertTrue(ctx.entities["lamp"].called)

    def test_expression_detects_condition_cycle(self) -> None:
        config = {
            "entities": {
                "lamp": {"type": "expression_lamp", "on": True, "load": 0.4, "called": False},
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
                    "type": "expression_trigger",
                    "event": "e1",
                    "conditions": ["c1"],
                    "actions": ["a1"],
                },
            },
        }

        ctx = build_all(config)

        async def run() -> None:
            await ctx.events["e1"].fire()

        with self.assertRaises(ValueError) as err:
            asyncio.run(run())
        self.assertIn("条件循环依赖", str(err.exception))


if __name__ == "__main__":
    unittest.main()
