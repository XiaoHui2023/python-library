"""export_type_schema / export_instance_schema 与 schema 监听器。"""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

import automation  # noqa: F401

from automation.assistant import Assistant
from automation.hub import Hub
from automation.listeners import InstanceSchemaListener, TypeSchemaListener
from automation.schema import export_instance_schema, export_type_schema

import support


class ExportTypeSchemaTests(unittest.TestCase):
    def test_top_level_sections(self) -> None:
        schema = export_type_schema()
        self.assertIn("entities", schema)
        self.assertIn("events", schema)
        self.assertIn("actions", schema)
        self.assertIn("triggers", schema)
        self.assertIn("composite_actions", schema)

    def test_composite_actions_meta(self) -> None:
        meta = export_type_schema()["composite_actions"]
        self.assertIn("description", meta)
        self.assertIn("fields", meta)
        self.assertIn("params", meta["fields"])
        self.assertIn("actions", meta["fields"])

    def test_time_entity_has_readonly_attributes(self) -> None:
        entities = export_type_schema()["entities"]
        self.assertIn("time", entities)
        info = entities["time"]
        self.assertIn("attributes", info)
        names = {a["name"] for a in info["attributes"]}
        self.assertEqual(names, {"hour", "minute", "second", "weekday"})
        hour = next(a for a in info["attributes"] if a["name"] == "hour")
        self.assertTrue(hour["readonly"])

    def test_variable_entity_config_fields(self) -> None:
        entities = export_type_schema()["entities"]
        self.assertIn("variable", entities)
        fields = entities["variable"]["config_fields"]
        self.assertIn("properties", fields)


class ExportInstanceSchemaTests(unittest.TestCase):
    def test_empty_hub(self) -> None:
        hub = Hub()
        inst = export_instance_schema(hub)
        self.assertEqual(inst["entities"], {})
        self.assertEqual(inst["events"], {})
        self.assertEqual(inst["triggers"], {})
        self.assertEqual(inst["actions"], {})

    def test_variable_entity_dynamic_attributes(self) -> None:
        config = {
            "entities": {
                "counter": {
                    "type": "variable",
                    "properties": {
                        "n": {
                            "type": "int",
                            "default": 7,
                            "description": "test counter",
                        },
                    },
                },
            },
        }
        hub = support.run_hub(config)
        inst = export_instance_schema(hub)
        self.assertIn("counter", inst["entities"])
        ent = inst["entities"]["counter"]
        self.assertEqual(ent["type"], "variable")
        self.assertIn("n", ent["attributes"])
        attr = ent["attributes"]["n"]
        self.assertEqual(attr["type"], "int")
        self.assertEqual(attr["description"], "test counter")
        self.assertFalse(attr["readonly"])
        self.assertIn("value", attr)

    def test_time_entity_runtime_attributes(self) -> None:
        config = {"entities": {"clock": {"type": "time"}}}
        hub = support.run_hub(config)
        inst = export_instance_schema(hub)
        ent = inst["entities"]["clock"]
        for key in ("hour", "minute", "second", "weekday"):
            self.assertIn(key, ent["attributes"])
            self.assertIn("value", ent["attributes"][key])
            self.assertTrue(ent["attributes"][key]["readonly"])

    def test_events_triggers_actions_summaries(self) -> None:
        config = {
            "entities": {"v": {"type": "variable", "properties": {}}},
            "events": {"e1": {"type": "every", "seconds": 60}},
            "actions": {
                "combo": {
                    "params": {},
                    "conditions": [],
                    "actions": [{"type": "log", "message": "x"}],
                },
            },
            "triggers": {
                "t1": {
                    "event": "e1",
                    "conditions": [],
                    "actions": [{"type": "log", "message": "y"}],
                },
            },
        }
        hub = support.run_hub(config)
        inst = export_instance_schema(hub)
        self.assertEqual(inst["events"]["e1"]["type"], "every")
        self.assertIn("config", inst["events"]["e1"])
        self.assertEqual(inst["events"]["e1"]["config"]["seconds"], 60)
        tr = inst["triggers"]["t1"]
        self.assertEqual(tr["event"], "e1")
        self.assertEqual(tr["actions_count"], 1)
        self.assertEqual(inst["actions"]["combo"]["actions_count"], 1)


class EntityRuntimeHelpersTests(unittest.TestCase):
    def test_get_attribute_values_time(self) -> None:
        hub = support.run_hub({"entities": {"t": {"type": "time"}}})
        ent = hub.entities["t"]
        values = ent.get_attribute_values()
        self.assertEqual(set(values.keys()), {"hour", "minute", "second", "weekday"})
        self.assertIsInstance(values["hour"], int)


class SchemaListenerTests(unittest.TestCase):
    def test_type_schema_listener_writes_json(self) -> None:
        async def run() -> None:
            with tempfile.TemporaryDirectory() as td:
                path = Path(td) / "nested" / "types.json"
                assistant = Assistant(TypeSchemaListener(path))
                await assistant.load({})
                self.assertTrue(path.is_file())
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn("entities", data)
                self.assertIn("time", data["entities"])

        asyncio.run(run())

    def test_instance_schema_listener_writes_json(self) -> None:
        async def run() -> None:
            with tempfile.TemporaryDirectory() as td:
                path = Path(td) / "instance.json"
                assistant = Assistant(InstanceSchemaListener(path))
                await assistant.load(
                    {
                        "entities": {
                            "v": {
                                "type": "variable",
                                "properties": {"a": {"type": "str", "default": "hi"}},
                            },
                        },
                    }
                )
                self.assertTrue(path.is_file())
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn("v", data["entities"])
                a = data["entities"]["v"]["attributes"]["a"]
                self.assertEqual(a["type"], "str")
                self.assertIn("value", a)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
