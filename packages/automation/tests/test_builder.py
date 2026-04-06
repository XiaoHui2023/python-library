import unittest
from typing import ClassVar

import automation  # noqa: F401

from automation.builder import build_all, build_section
from automation.context import AutomationContext
from automation.core.entity import Entity


class SampleEntity(Entity):
    _type: ClassVar[str] = "sample_entity"
    value: int = 0


class BuilderTests(unittest.TestCase):
    def test_build_section_creates_entity(self) -> None:
        objs = build_section(
            "entities",
            {"a": {"type": "sample_entity", "value": 42}},
        )
        self.assertIn("a", objs)
        self.assertEqual(objs["a"].instance_name, "a")
        self.assertEqual(objs["a"].value, 42)

    def test_build_section_missing_type_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            build_section("entities", {"x": {"value": 1}})
        self.assertIn("缺少 type", str(ctx.exception))

    def test_build_all_empty_sections(self) -> None:
        ctx = build_all({})
        self.assertIsInstance(ctx, AutomationContext)
        self.assertEqual(ctx.entities, {})
        self.assertEqual(ctx.triggers, {})


if __name__ == "__main__":
    unittest.main()
