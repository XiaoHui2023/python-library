import unittest
from typing import ClassVar

import automation  # noqa: F401

from automation.core.entity import Entity
from automation.hub import Hub


class ParserLamp(Entity):
    _type: ClassVar[str] = "parser_lamp"
    on: bool = True


class ExpressionParserTests(unittest.TestCase):
    def test_parse_entity_field(self) -> None:
        hub = Hub()
        hub.entities["lamp"] = ParserLamp(instance_name="lamp", on=True)
        r = hub.renderer
        r.validate_expr("{entity.lamp.on}")
        self.assertTrue(r.eval_bool("{entity.lamp.on}"))

    def test_validate_token_unknown_entity_raises(self) -> None:
        hub = Hub()
        with self.assertRaises(ValueError) as ctx:
            hub.renderer.validate_token("entity.missing.on")
        self.assertIn("Entity 'missing' not found", str(ctx.exception))

    def test_validate_expr_syntax_error_raises(self) -> None:
        hub = Hub()
        hub.entities["lamp"] = ParserLamp(instance_name="lamp", on=True)
        with self.assertRaises(ValueError) as ctx:
            hub.renderer.validate_expr("{entity.lamp.on} +")
        self.assertIn("Syntax error", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
