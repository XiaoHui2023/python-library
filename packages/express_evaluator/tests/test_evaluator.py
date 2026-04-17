from __future__ import annotations

import unittest

from express_evaluator import Evaluator
from express_evaluator.errors import (
    ExpressionSyntaxError,
    UndefinedVariableError,
    UnsafeExpressionError,
)


class _Sample:
    def __init__(self, ok: bool) -> None:
        self.ok = ok


class TestEvaluatorEvaluate(unittest.TestCase):
    def setUp(self) -> None:
        self.ev = Evaluator()

    def test_literal_constants(self) -> None:
        self.assertEqual(self.ev.evaluate("1", {}), 1)
        self.assertEqual(self.ev.evaluate("'hi'", {}), "hi")
        self.assertIs(self.ev.evaluate("True", {}), True)

    def test_list_and_tuple(self) -> None:
        self.assertEqual(self.ev.evaluate("[1, 2]", {}), [1, 2])
        self.assertEqual(self.ev.evaluate("(1, 2)", {}), (1, 2))

    def test_callable_invocation(self) -> None:
        self.assertEqual(self.ev("1", {}), 1)

    def test_comparison_chain(self) -> None:
        self.assertIs(self.ev.evaluate("1 < 2 < 3", {}), True)

    def test_membership_and_is(self) -> None:
        self.assertIs(self.ev.evaluate("1 in [1, 2]", {}), True)
        self.assertIs(self.ev.evaluate("1 not in [2, 3]", {}), True)
        self.assertIs(self.ev.evaluate("1 is 1", {}), True)
        self.assertIs(self.ev.evaluate("1 is not 2", {}), True)

    def test_bool_ops_short_circuit(self) -> None:
        self.assertIs(self.ev.evaluate("False or True", {}), True)
        self.assertIs(self.ev.evaluate("True and False", {}), False)

    def test_unary_not(self) -> None:
        self.assertIs(self.ev.evaluate("not True", {}), False)

    def test_placeholder_simple(self) -> None:
        self.assertEqual(self.ev.evaluate("{x}", {"x": 7}), 7)

    def test_placeholder_nested_path(self) -> None:
        self.assertEqual(self.ev.evaluate("{a.b}", {"a": {"b": 3}}), 3)

    def test_any_all(self) -> None:
        self.assertIs(self.ev.evaluate("any([True, False])", {}), True)
        self.assertIs(self.ev.evaluate("all([True, True])", {}), True)
        self.assertIs(self.ev.evaluate("all([True, False])", {}), False)

    def test_any_all_with_attr(self) -> None:
        items = [_Sample(True), _Sample(False)]
        self.assertIs(self.ev.evaluate('any({items}, "ok")', {"items": items}), True)
        self.assertIs(self.ev.evaluate('all({items}, "ok")', {"items": items}), False)

    def test_any_with_generator(self) -> None:
        # 列表字面量中避免一元负号（USub 未在默认语法中启用）
        self.assertIs(
            self.ev.evaluate("any(x > 0 for x in [1, 0])", {}),
            True,
        )

    def test_list_comprehension(self) -> None:
        self.assertEqual(
            self.ev.evaluate("[i for i in [1, 2]]", {}),
            [1, 2],
        )

    def test_attribute_on_placeholder_value(self) -> None:
        class Box:
            n = 5

        self.assertEqual(self.ev.evaluate("{b}.n", {"b": Box()}), 5)

    def test_mapping_attribute_style(self) -> None:
        self.assertEqual(self.ev.evaluate("{m}.k", {"m": {"k": 9}}), 9)


class TestEvaluatorErrors(unittest.TestCase):
    def setUp(self) -> None:
        self.ev = Evaluator()

    def test_invalid_expression_syntax(self) -> None:
        with self.assertRaises(ExpressionSyntaxError):
            self.ev.evaluate("(", {})

    def test_undefined_name(self) -> None:
        with self.assertRaises(UndefinedVariableError):
            self.ev.evaluate("missing", {})

    def test_unsafe_binop_not_supported(self) -> None:
        with self.assertRaises(UnsafeExpressionError):
            self.ev.evaluate("1 + 1", {})

    def test_keyword_arguments_on_call(self) -> None:
        with self.assertRaises(UnsafeExpressionError):
            self.ev.evaluate("any([], x=1)", {})

    def test_private_attribute_forbidden(self) -> None:
        with self.assertRaises(UnsafeExpressionError):
            self.ev.evaluate("{o}.__class__", {"o": object()})

    def test_strict_placeholder_missing_path(self) -> None:
        ev = Evaluator(strict_undefined=True)
        with self.assertRaises(UndefinedVariableError):
            ev.evaluate("{nope}", {})

    def test_non_strict_placeholder_missing_path_yields_none(self) -> None:
        ev = Evaluator(strict_undefined=False)
        self.assertIsNone(ev.evaluate("{nope}", {}))


class TestEvaluatorSyntaxSubset(unittest.TestCase):
    def test_without_comprehensions_listcomp_rejected(self) -> None:
        ev = Evaluator(
            syntaxs=[
                "literals",
                "comparisons",
                "bool_ops",
                "unary_not",
                "attribute_access",
                "placeholders",
                "builtin_any_all",
            ]
        )
        with self.assertRaises(UnsafeExpressionError):
            ev.evaluate("[x for x in [1]]", {})


if __name__ == "__main__":
    unittest.main()
