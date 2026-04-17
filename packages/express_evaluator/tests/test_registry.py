from __future__ import annotations

import unittest

from express_evaluator.registry import (
    get_syntax,
    get_syntaxs,
    has_syntax,
    iter_syntaxes,
    syntax_names,
)
from express_evaluator.syntax import load_syntax_modules
from express_evaluator.errors import SyntaxRegistrationError


class TestRegistryAfterLoad(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load_syntax_modules()

    def test_default_syntax_names_present(self) -> None:
        names = set(syntax_names())
        for expected in (
            "attribute_access",
            "bool_ops",
            "builtin_any_all",
            "comparisons",
            "comprehensions",
            "literals",
            "placeholders",
            "unary_not",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, names)

    def test_has_syntax_true(self) -> None:
        self.assertTrue(has_syntax("literals"))

    def test_has_syntax_false(self) -> None:
        self.assertFalse(has_syntax("definitely_not_a_registered_syntax_name"))

    def test_get_syntax_returns_spec(self) -> None:
        spec = get_syntax("literals")
        self.assertEqual(spec.name, "literals")

    def test_get_syntax_missing_raises(self) -> None:
        with self.assertRaises(SyntaxRegistrationError):
            get_syntax("missing_syntax_xyz")

    def test_get_syntaxs_order(self) -> None:
        specs = get_syntaxs(["literals", "comparisons"])
        self.assertEqual([s.name for s in specs], ["literals", "comparisons"])

    def test_iter_syntaxes_non_empty(self) -> None:
        specs = iter_syntaxes()
        self.assertGreater(len(specs), 0)
        self.assertTrue(all(s.name for s in specs))


if __name__ == "__main__":
    unittest.main()
