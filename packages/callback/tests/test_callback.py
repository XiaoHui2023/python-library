import unittest
from typing import ClassVar

from callback import Callback


class CallbackTests(unittest.TestCase):
    def tearDown(self) -> None:
        Callback.function_registry.clear()

    def test_trigger_invokes_registered_handler(self) -> None:
        class Inc(Callback):
            callback_name: str = "Inc"
            name: str
            data: int

        class Holder:
            def __init__(self) -> None:
                @Inc
                def _(cb: Inc) -> None:
                    cb.data += 1

        Holder()
        cb = Inc.trigger(name="test", data=1)
        self.assertEqual(cb.data, 2)

    def test_field_names_simple_subclass(self) -> None:
        class E(Callback):
            a: int
            b: str

        names = E._field_names()
        self.assertEqual(names, ["a", "b"])
        self.assertNotIn("function_registry", names)

    def test_field_names_skips_classvar(self) -> None:
        class E(Callback):
            meta: ClassVar[str] = "E"
            value: int

        self.assertEqual(E._field_names(), ["value"])

    def test_field_names_skips_underscore_prefixed(self) -> None:
        class E(Callback):
            _internal: int
            public: str

        self.assertEqual(E._field_names(), ["public"])

    def test_field_names_classvar_and_underscore_together(self) -> None:
        class E(Callback):
            cv: ClassVar[int] = 0
            _hidden: float
            ok: bool

        self.assertEqual(E._field_names(), ["ok"])

    def test_field_names_single_inheritance_order(self) -> None:
        class Base(Callback):
            x: int

        class Sub(Base):
            y: str

        self.assertEqual(Base._field_names(), ["x"])
        self.assertEqual(Sub._field_names(), ["x", "y"])

    def test_field_names_multiple_inheritance_mro_order(self) -> None:
        class A(Callback):
            a: int

        class B(Callback):
            b: int

        class C(A, B):
            c: int

        # reversed(MRO) 中先 B 后 A 再 C，与实现一致
        self.assertEqual(C._field_names(), ["b", "a", "c"])

    def test_field_names_subclass_override_preserves_first_key_order(self) -> None:
        class Base(Callback):
            shared: int

        class Sub(Base):
            shared: str
            extra: bool

        # shared 在 Base 中先出现，Sub 覆盖不改变 dict 中键顺序
        names = Sub._field_names()
        self.assertEqual(names[0], "shared")
        self.assertLess(names.index("shared"), names.index("extra"))
        self.assertEqual(names, ["shared", "extra"])

    def test_init_positional_maps_by_field_names_order(self) -> None:
        class P(Callback):
            first: int
            second: str

        p = P(1, "x")
        self.assertEqual(p.first, 1)
        self.assertEqual(p.second, "x")

    def test_init_too_many_positional_raises(self) -> None:
        class P(Callback):
            only: int

        with self.assertRaises(ValueError):
            P(1, 2)

    def test_init_unknown_keyword_raises(self) -> None:
        class P(Callback):
            a: int

        with self.assertRaises(ValueError):
            P(a=1, not_a_field=2)

    def test_decorator_rejects_async_on_sync_callback(self) -> None:
        class SyncCb(Callback):
            x: int

        with self.assertRaises(ValueError):

            @SyncCb
            async def _handler(cb: SyncCb) -> None:  # noqa: ARG001
                pass

    def test_decorator_rejects_sync_on_async_callback(self) -> None:
        class AsyncCb(Callback):
            _async = True
            x: int

        with self.assertRaises(ValueError):

            @AsyncCb
            def _handler(cb: AsyncCb) -> None:  # noqa: ARG001
                pass

    def test_registered_handler_with_no_parameters(self) -> None:
        class E(Callback):
            x: int

        called: list[int] = []

        @E
        def _handler() -> None:
            called.append(1)

        E.trigger(x=0)
        self.assertEqual(called, [1])

    def test_trigger_with_no_registered_handlers(self) -> None:
        class Quiet(Callback):
            flag: bool

        q = Quiet.trigger(flag=True)
        self.assertTrue(q.flag)

    def test_get_all_includes_defined_subclass(self) -> None:
        class G(Callback):
            v: int

        self.assertIn(G, Callback.get_all())


class AsyncCallbackTests(unittest.IsolatedAsyncioTestCase):
    def tearDown(self) -> None:
        Callback.function_registry.clear()

    async def test_atrigger_invokes_async_handler(self) -> None:
        class AC(Callback):
            _async = True
            n: int

        seen: list[int] = []

        @AC
        async def h(cb: AC) -> None:
            seen.append(cb.n)

        await AC.atrigger(n=7)
        self.assertEqual(seen, [7])

    async def test_atrigger_registered_no_arg_async_handler(self) -> None:
        class AC(Callback):
            _async = True
            n: int

        called = False

        @AC
        async def h() -> None:
            nonlocal called
            called = True

        await AC.atrigger(n=1)
        self.assertTrue(called)


if __name__ == "__main__":
    unittest.main()
