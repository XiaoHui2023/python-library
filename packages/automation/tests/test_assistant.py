import asyncio
import unittest

import automation  # noqa: F401

from automation.assistant import Assistant


class AssistantTests(unittest.TestCase):
    def test_load_empty_dict(self) -> None:
        async def run() -> None:
            assistant = Assistant()
            await assistant.load({})
            self.assertEqual(assistant.entities, {})
            self.assertEqual(assistant.triggers, {})

        asyncio.run(run())

    def test_export_schema_returns_dict(self) -> None:
        schema = Assistant.export_schema()
        self.assertIsInstance(schema, dict)

    def test_export_schema_includes_registered_entities(self) -> None:
        schema = Assistant.export_schema()
        self.assertIn("entities", schema)
        self.assertIn("time", schema["entities"])
        self.assertIn("variable", schema["entities"])


if __name__ == "__main__":
    unittest.main()
