import asyncio
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
    def test_expression_can_combine_entity_fields(self) -> None:
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
            "triggers": {
                "t1": {
                    "event": "e1",
                    "conditions": [
                        "{entity.lamp.on} and {entity.lamp.load} < 0.8",
                    ],
                    "actions": [
                        {
                            "type": "call_entity_method",
                            "entity": "lamp",
                            "method": "record",
                            "args": {},
                        },
                    ],
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

    def test_load_fails_when_condition_references_unknown_entity(self) -> None:
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
            "triggers": {
                "t1": {
                    "event": "e1",
                    "conditions": ["{entity.not_lamp.on}"],
                    "actions": [
                        {
                            "type": "call_entity_method",
                            "entity": "lamp",
                            "method": "record",
                            "args": {},
                        },
                    ],
                },
            },
        }

        async def run() -> None:
            hub = Hub()
            await loader.load(hub, config)

        with self.assertRaises(ValueError) as ctx:
            asyncio.run(run())
        self.assertIn("not_lamp", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
