from __future__ import annotations

import asyncio
import unittest
from typing import Any

from observer import ObserverBus, ObserverContext, observe_methods


class ObserverBusTests(unittest.TestCase):
    def test_subscribe_invokes_on_emit(self) -> None:
        bus = ObserverBus()
        seen: list[str] = []

        def cb(ctx: ObserverContext) -> None:
            seen.append(ctx.phase)

        bus.subscribe(cb)
        ctx = ObserverContext(
            call_id="1",
            instance=None,
            owner=None,
            cls=object,
            cls_name="object",
            method_name="m",
            qualname="m",
            method_kind="static",
            args=(),
            kwargs={},
            phase="after",
        )
        bus.emit(ctx)
        self.assertEqual(seen, ["after"])

    def test_subscribe_returns_callback(self) -> None:
        bus = ObserverBus()

        def cb(ctx: ObserverContext) -> None:
            pass

        self.assertIs(bus.subscribe(cb), cb)

    def test_duplicate_subscribe_same_filters_is_idempotent(self) -> None:
        bus = ObserverBus()
        count = 0

        def cb(ctx: ObserverContext) -> None:
            nonlocal count
            count += 1

        bus.subscribe(cb, phase="after")
        bus.subscribe(cb, phase="after")
        bus.emit(
            ObserverContext(
                call_id="1",
                instance=None,
                owner=None,
                cls=object,
                cls_name="object",
                method_name="m",
                qualname="m",
                method_kind="static",
                args=(),
                kwargs={},
                phase="after",
            )
        )
        self.assertEqual(count, 1)

    def test_same_callback_different_filters_both_fire(self) -> None:
        bus = ObserverBus()
        phases: list[str] = []

        def cb(ctx: ObserverContext) -> None:
            phases.append(ctx.phase)

        bus.subscribe(cb, phase="before")
        bus.subscribe(cb, phase="after")
        bus.emit(
            ObserverContext(
                call_id="1",
                instance=None,
                owner=None,
                cls=object,
                cls_name="object",
                method_name="m",
                qualname="m",
                method_kind="static",
                args=(),
                kwargs={},
                phase="before",
            )
        )
        bus.emit(
            ObserverContext(
                call_id="2",
                instance=None,
                owner=None,
                cls=object,
                cls_name="object",
                method_name="m",
                qualname="m",
                method_kind="static",
                args=(),
                kwargs={},
                phase="after",
            )
        )
        self.assertEqual(phases, ["before", "after"])

    def test_unsubscribe_removes_callback(self) -> None:
        bus = ObserverBus()
        seen: list[int] = []

        def cb(ctx: ObserverContext) -> None:
            seen.append(1)

        bus.subscribe(cb)
        bus.unsubscribe(cb)
        bus.emit(
            ObserverContext(
                call_id="1",
                instance=None,
                owner=None,
                cls=object,
                cls_name="object",
                method_name="m",
                qualname="m",
                method_kind="static",
                args=(),
                kwargs={},
            )
        )
        self.assertEqual(seen, [])

    def test_callback_decorator_registers(self) -> None:
        bus = ObserverBus()
        seen: list[str] = []

        @bus.callback(phase="after", cls_name="Svc")
        def cb(ctx: ObserverContext) -> None:
            seen.append(ctx.method_name)

        bus.emit(
            ObserverContext(
                call_id="1",
                instance=None,
                owner=None,
                cls=type("Svc", (), {}),
                cls_name="Svc",
                method_name="run",
                qualname="Svc.run",
                method_kind="instance",
                args=(),
                kwargs={},
                phase="after",
            )
        )
        self.assertEqual(seen, ["run"])

    def test_callback_multiple_filters_all_must_match(self) -> None:
        bus = ObserverBus()
        seen: list[int] = []

        @bus.callback(phase="after", method_name="run")
        def cb(_: ObserverContext) -> None:
            seen.append(1)

        bus.emit(
            ObserverContext(
                call_id="1",
                instance=None,
                owner=None,
                cls=object,
                cls_name="object",
                method_name="other",
                qualname="object.other",
                method_kind="static",
                args=(),
                kwargs={},
                phase="after",
            )
        )
        self.assertEqual(seen, [])

        bus.emit(
            ObserverContext(
                call_id="2",
                instance=None,
                owner=None,
                cls=object,
                cls_name="object",
                method_name="run",
                qualname="object.run",
                method_kind="static",
                args=(),
                kwargs={},
                phase="after",
            )
        )
        self.assertEqual(seen, [1])

    def test_callback_decorator_rejects_invalid_filter_keys(self) -> None:
        bus = ObserverBus()

        with self.assertRaises(ValueError) as ar:
            @bus.callback(not_a_context_field=1)
            def cb(ctx: ObserverContext) -> None:
                pass

        self.assertIn("invalid callback filters", str(ar.exception))

    def test_emit_listener_exception_does_not_propagate(self) -> None:
        bus = ObserverBus()

        def bad(_: ObserverContext) -> None:
            raise RuntimeError("boom")

        bus.subscribe(bad)

        ctx = ObserverContext(
            call_id="1",
            instance=None,
            owner=None,
            cls=object,
            cls_name="object",
            method_name="m",
            qualname="m",
            method_kind="static",
            args=(),
            kwargs={},
        )
        bus.emit(ctx)

    def test_emit_order_matches_subscription_order(self) -> None:
        bus = ObserverBus()
        order: list[int] = []

        def first(_: ObserverContext) -> None:
            order.append(1)

        def second(_: ObserverContext) -> None:
            order.append(2)

        bus.subscribe(first)
        bus.subscribe(second)
        bus.emit(
            ObserverContext(
                call_id="1",
                instance=None,
                owner=None,
                cls=object,
                cls_name="object",
                method_name="m",
                qualname="m",
                method_kind="static",
                args=(),
                kwargs={},
            )
        )
        self.assertEqual(order, [1, 2])


class ObserveMethodsTests(unittest.TestCase):
    def test_instance_method_emits_before_and_after(self) -> None:
        bus = ObserverBus()
        phases: list[str] = []

        bus.subscribe(lambda ctx: phases.append(ctx.phase))

        @observe_methods(bus)
        class Svc:
            def add(self, a: int, b: int) -> int:
                return a + b

        self.assertEqual(Svc().add(1, 2), 3)
        self.assertEqual(phases, ["before", "after"])

    def test_emit_before_false_skips_before_phase(self) -> None:
        bus = ObserverBus()
        phases: list[str] = []

        bus.subscribe(lambda ctx: phases.append(ctx.phase))

        @observe_methods(bus, emit_before=False)
        class Svc:
            def add(self, a: int, b: int) -> int:
                return a + b

        self.assertEqual(Svc().add(1, 2), 3)
        self.assertEqual(phases, ["after"])

    def test_same_call_id_across_phases_for_sync_call(self) -> None:
        bus = ObserverBus()
        ids: list[str] = []

        bus.subscribe(lambda ctx: ids.append(ctx.call_id))

        @observe_methods(bus)
        class Svc:
            def add(self, a: int, b: int) -> int:
                return a + b

        Svc().add(1, 2)
        self.assertEqual(len(ids), 2)
        self.assertEqual(ids[0], ids[1])

    def test_error_phase_then_exception_reraised(self) -> None:
        bus = ObserverBus()
        phases: list[str] = []

        bus.subscribe(lambda ctx: phases.append(ctx.phase))

        @observe_methods(bus)
        class Svc:
            def boom(self) -> None:
                raise ValueError("x")

        with self.assertRaises(ValueError):
            Svc().boom()

        self.assertEqual(phases, ["before", "error"])

    def test_classmethod_context_owner_and_pure_args(self) -> None:
        bus = ObserverBus()
        snapshots: list[tuple[Any, Any, tuple[Any, ...]]] = []

        def capture(ctx: ObserverContext) -> None:
            if ctx.phase == "after":
                snapshots.append((ctx.instance, ctx.owner, ctx.args))

        bus.subscribe(capture)

        @observe_methods(bus)
        class Svc:
            @classmethod
            def build(cls, name: str) -> Svc:
                return cls()

        inst = Svc.build("n")
        self.assertIsInstance(inst, Svc)
        self.assertEqual(len(snapshots), 1)
        instance, owner, args = snapshots[0]
        self.assertIsNone(instance)
        self.assertIs(owner, Svc)
        self.assertEqual(args, ("n",))

    def test_staticmethod_context(self) -> None:
        bus = ObserverBus()
        kinds: list[str] = []
        owners: list[Any] = []

        def capture(ctx: ObserverContext) -> None:
            if ctx.phase == "after":
                kinds.append(ctx.method_kind)
                owners.append(ctx.owner)

        bus.subscribe(capture)

        @observe_methods(bus)
        class Svc:
            @staticmethod
            def ping(msg: str) -> str:
                return msg

        self.assertEqual(Svc.ping("hi"), "hi")
        self.assertEqual(kinds, ["static"])
        self.assertIsNone(owners[0])

    def test_property_not_wrapped(self) -> None:
        bus = ObserverBus()

        @observe_methods(bus)
        class Svc:
            @property
            def x(self) -> int:
                return 1

        self.assertIsInstance(Svc.x, property)

    def test_private_method_skipped_by_default(self) -> None:
        bus = ObserverBus()
        method_names: list[str] = []

        bus.subscribe(lambda ctx: method_names.append(ctx.method_name))

        @observe_methods(bus)
        class Svc:
            def _hidden(self) -> int:
                return 2

            def ok(self) -> int:
                return self._hidden()

        self.assertEqual(Svc().ok(), 2)
        self.assertEqual(method_names, ["ok", "ok"])
        self.assertNotIn("_hidden", method_names)

    def test_include_private_wraps_dunder_named_callable(self) -> None:
        bus = ObserverBus()
        method_names: list[str] = []

        bus.subscribe(lambda ctx: method_names.append(ctx.method_name))

        @observe_methods(bus, include_private=True)
        class Svc:
            def _hidden(self) -> int:
                return 7

        self.assertEqual(Svc()._hidden(), 7)
        self.assertIn("_hidden", method_names)

    def test_subclass_methods_observed(self) -> None:
        bus = ObserverBus()
        names: list[str] = []

        bus.subscribe(lambda ctx: names.append(ctx.method_name) if ctx.phase == "after" else None)

        @observe_methods(bus)
        class Base:
            def a(self) -> int:
                return 1

        class Child(Base):
            def b(self) -> int:
                return 2

        self.assertEqual(Child().a(), 1)
        self.assertEqual(Child().b(), 2)
        self.assertIn("a", names)
        self.assertIn("b", names)

    def test_instance_context_cls_is_runtime_type(self) -> None:
        bus = ObserverBus()
        cls_names: list[str] = []

        bus.subscribe(
            lambda ctx: cls_names.append(ctx.cls_name) if ctx.phase == "after" else None
        )

        @observe_methods(bus)
        class Base:
            def tag(self) -> str:
                return "base"

        class Child(Base):
            def tag(self) -> str:
                return "child"

        self.assertEqual(Base().tag(), "base")
        self.assertEqual(Child().tag(), "child")
        self.assertEqual(cls_names, ["Base", "Child"])

    def test_double_decorate_does_not_double_wrap(self) -> None:
        bus = ObserverBus()
        phases: list[str] = []

        bus.subscribe(lambda ctx: phases.append(ctx.phase))

        @observe_methods(bus)
        @observe_methods(bus)
        class Svc:
            def run(self) -> int:
                return 1

        self.assertEqual(Svc().run(), 1)
        self.assertEqual(phases, ["before", "after"])

    def test_bus_observe_delegates_to_observe_methods(self) -> None:
        bus = ObserverBus()
        phases: list[str] = []

        bus.subscribe(lambda ctx: phases.append(ctx.phase))

        @bus.observe()
        class Svc:
            def run(self) -> int:
                return 5

        self.assertEqual(Svc().run(), 5)
        self.assertEqual(phases, ["before", "after"])


class AsyncObserveMethodsTests(unittest.TestCase):
    def test_async_instance_method_phases(self) -> None:
        bus = ObserverBus()
        phases: list[str] = []

        bus.subscribe(lambda ctx: phases.append(ctx.phase))

        @observe_methods(bus)
        class Svc:
            async def fetch(self, n: int) -> int:
                await asyncio.sleep(0)
                return n * 2

        async def main() -> int:
            return await Svc().fetch(3)

        self.assertEqual(asyncio.run(main()), 6)
        self.assertEqual(phases, ["before", "after"])

    def test_async_error_phase(self) -> None:
        bus = ObserverBus()
        phases: list[str] = []

        bus.subscribe(lambda ctx: phases.append(ctx.phase))

        @observe_methods(bus)
        class Svc:
            async def boom(self) -> None:
                raise OSError("async")

        async def main() -> None:
            await Svc().boom()

        with self.assertRaises(OSError):
            asyncio.run(main())

        self.assertEqual(phases, ["before", "error"])

    def test_async_emit_before_false(self) -> None:
        bus = ObserverBus()
        phases: list[str] = []

        bus.subscribe(lambda ctx: phases.append(ctx.phase))

        @observe_methods(bus, emit_before=False)
        class Svc:
            async def fetch(self) -> int:
                return 9

        async def main() -> int:
            return await Svc().fetch()

        self.assertEqual(asyncio.run(main()), 9)
        self.assertEqual(phases, ["after"])


class InitSubclassChainTests(unittest.TestCase):
    def test_preserves_existing_init_subclass(self) -> None:
        bus = ObserverBus()
        log: list[str] = []

        class Base:
            def __init_subclass__(cls, **kwargs: Any) -> None:
                super().__init_subclass__(**kwargs)
                log.append("base_hook")

        @observe_methods(bus)
        class Observed(Base):
            def run(self) -> None:
                pass

        class Child(Observed):
            pass

        self.assertIn("base_hook", log)


if __name__ == "__main__":
    unittest.main()
