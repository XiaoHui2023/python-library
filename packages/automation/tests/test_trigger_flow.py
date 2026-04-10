import asyncio
import unittest
from typing import ClassVar

import automation  # noqa: F401

from automation import loader
from automation.core.entity import Entity
from automation.core.event import Event
from automation.hub import Hub


class PressEvent(Event):
    _type: ClassVar[str] = "press"


_calls: list[str] = []


class TriggerFlowLamp(Entity):
    """单一实体类型，通过配置 on 与共享 _calls 验证是否执行 record。"""

    _type: ClassVar[str] = "trigger_flow_lamp"
    on: bool = False

    def record(self) -> None:
        _calls.append("done")


class TriggerFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        _calls.clear()

    def test_fire_runs_action_when_condition_true(self) -> None:
        config = {
            "entities": {"lamp": {"type": "trigger_flow_lamp", "on": True}},
            "events": {"e1": {"type": "press"}},
            "triggers": {
                "t1": {
                    "event": "e1",
                    "conditions": ["{entity.lamp.on}"],
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
            await hub.events["e1"].fire()

        asyncio.run(run())
        self.assertEqual(_calls, ["done"])

    def test_fire_skips_action_when_condition_false(self) -> None:
        config = {
            "entities": {"lamp": {"type": "trigger_flow_lamp", "on": False}},
            "events": {"e1": {"type": "press"}},
            "triggers": {
                "t1": {
                    "event": "e1",
                    "conditions": ["{entity.lamp.on}"],
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
            await hub.events["e1"].fire()

        asyncio.run(run())
        self.assertEqual(_calls, [])


if __name__ == "__main__":
    unittest.main()
