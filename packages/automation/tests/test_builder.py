import unittest
from typing import ClassVar

import automation  # noqa: F401

import support

from automation import loader
from automation.core.entity import Entity
from automation.errors import ConfigLoadError, LoadErrorCode

class SampleEntity(Entity):
    _type: ClassVar[str] = "sample_entity"
    value: int = 0


class LoaderBuildSectionTests(unittest.TestCase):
    def test_build_section_creates_entity(self) -> None:
        objs = loader.build_section(
            "entities",
            {"a": {"type": "sample_entity", "value": 42}},
        )
        self.assertIn("a", objs)
        self.assertEqual(objs["a"].instance_name, "a")
        self.assertEqual(objs["a"].value, 42)

    def test_build_section_missing_type_raises(self) -> None:
        with self.assertRaises(ConfigLoadError) as ctx:
            loader.build_section("entities", {"x": {"value": 1}})
        self.assertEqual(ctx.exception.code, LoadErrorCode.MISSING_TYPE)
        self.assertEqual(ctx.exception.section, "entities")
        self.assertEqual(ctx.exception.instance, "x")

    def test_load_empty_config(self) -> None:
        hub = support.run_hub({})
        self.assertEqual(hub.entities, {})
        self.assertEqual(hub.events, {})
        self.assertEqual(hub.actions, {})
        self.assertEqual(hub.triggers, {})


if __name__ == "__main__":
    unittest.main()
