import unittest
from typing import ClassVar

import automation  # noqa: F401

from automation.builtins.condition.expression.parser import (
    parse_expr,
    validate_ast,
    validate_placeholder,
)
from automation.core.entity import Entity
from automation.hub import Hub


class ParserLamp(Entity):
    _type: ClassVar[str] = "parser_lamp"
    on: bool = True


class ExpressionParserTests(unittest.TestCase):
    def test_parse_entity_field(self) -> None:
        hub = Hub()
        hub.entities["lamp"] = ParserLamp(instance_name="lamp", on=True)
        tree, placeholders = parse_expr("{lamp.on}", hub)
        self.assertTrue(placeholders)
        validate_ast(tree)

    def test_validate_placeholder_unknown_entity_raises(self) -> None:
        hub = Hub()
        with self.assertRaises(ValueError) as ctx:
            validate_placeholder("missing.attr", hub)
        self.assertIn("Entity 'missing' not found", str(ctx.exception))

    def test_parse_syntax_error_raises(self) -> None:
        hub = Hub()
        hub.entities["lamp"] = ParserLamp(instance_name="lamp", on=True)
        with self.assertRaises(ValueError) as ctx:
            parse_expr("{lamp.on} +", hub)
        self.assertIn("Syntax error", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
