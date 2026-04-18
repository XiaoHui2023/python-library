from __future__ import annotations

import unittest
from typing import TYPE_CHECKING, ClassVar

from callback import Callback

if TYPE_CHECKING:

    class _UnavailableAtRuntime:
        """模拟仅在类型检查时可解析的类型名；运行时不存在于 globals。"""


class CallbackFutureAnnotationsTests(unittest.TestCase):
    def tearDown(self) -> None:
        Callback.function_registry.clear()

    def test_field_names_uses_string_annotations(self) -> None:
        class E(Callback):
            a: int
            b: str

        self.assertEqual(E._field_names(), ["a", "b"])

    def test_field_names_skips_classvar_string(self) -> None:
        class E(Callback):
            meta: ClassVar[str] = "E"
            value: int

        self.assertEqual(E._field_names(), ["value"])

    def test_field_names_typechecking_forward_ref(self) -> None:
        class E(Callback):
            ref: _UnavailableAtRuntime

        self.assertEqual(E._field_names(), ["ref"])
        sentinel = object()
        cb = E.trigger(ref=sentinel)
        self.assertIs(cb.ref, sentinel)

    def test_trigger_kwarg_with_typechecking_forward_ref(self) -> None:
        class E(Callback):
            ctx: _UnavailableAtRuntime

        sentinel = object()
        cb = E.trigger(ctx=sentinel)
        self.assertIs(cb.ctx, sentinel)


if __name__ == "__main__":
    unittest.main()
