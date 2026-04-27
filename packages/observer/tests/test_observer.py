from __future__ import annotations

import asyncio
import logging
import unittest
from typing import Any

from observer import ObserverBus, ObserverContext, observe_methods


def _ctx(**overrides: Any) -> ObserverContext:
    defaults: dict[str, Any] = dict(
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
    defaults.update(overrides)
    return ObserverContext(**defaults)


class ObserverBusTests(unittest.TestCase):
    def test_subscribe_invokes_on_emit(self) -> None:
        seen: list[str] = []
        with ObserverBus(max_workers=1) as bus:

            def cb(ctx: ObserverContext) -> None:
                seen.append(ctx.phase)

            bus.subscribe(cb)
            bus.emit(_ctx(phase="after"))
        self.assertEqual(seen, ["after"])

    def test_subscribe_returns_callback(self) -> None:
        with ObserverBus(max_workers=1) as bus:

            def cb(ctx: ObserverContext) -> None:
                pass

            self.assertIs(bus.subscribe(cb), cb)

    def test_subscribe_rejects_invalid_filter_keys(self) -> None:
        with ObserverBus(max_workers=1) as bus:

            def cb(_: ObserverContext) -> None:
                pass

            with self.assertRaises(ValueError) as ar:
                bus.subscribe(cb, not_a_field=1)
            self.assertIn("invalid callback filters", str(ar.exception))

    def test_subscribe_after_close_raises(self) -> None:
        bus = ObserverBus(max_workers=1)
        bus.close(wait=True)

        def cb(_: ObserverContext) -> None:
            pass

        with self.assertRaises(RuntimeError) as ar:
            bus.subscribe(cb)
        self.assertIn("closed", str(ar.exception).lower())

    def test_emit_after_close_does_not_invoke_callbacks(self) -> None:
        seen: list[int] = []
        bus = ObserverBus(max_workers=1)

        def cb(_: ObserverContext) -> None:
            seen.append(1)

        bus.subscribe(cb)
        bus.emit(_ctx())
        bus.close(wait=True)
        self.assertEqual(seen, [1])

        bus.emit(_ctx(call_id="2"))
        self.assertEqual(seen, [1])

    def test_context_manager_closes_bus(self) -> None:
        bus: ObserverBus | None = None
        with ObserverBus(max_workers=1) as b:
            bus = b
            self.assertIsInstance(bus, ObserverBus)
        self.assertIsNotNone(bus)
        with self.assertRaises(RuntimeError):
            bus.subscribe(lambda _: None)

    def test_close_is_idempotent(self) -> None:
        bus = ObserverBus(max_workers=1)
        bus.close(wait=True)
        bus.close(wait=True)

    def test_duplicate_subscribe_same_filters_is_idempotent(self) -> None:
        count = 0
        with ObserverBus(max_workers=1) as bus:

            def cb(ctx: ObserverContext) -> None:
                nonlocal count
                count += 1

            bus.subscribe(cb, phase="after")
            bus.subscribe(cb, phase="after")
            bus.emit(_ctx(phase="after"))
        self.assertEqual(count, 1)

    def test_same_callback_different_filters_both_fire(self) -> None:
        phases: list[str] = []
        with ObserverBus(max_workers=1) as bus:

            def cb(ctx: ObserverContext) -> None:
                phases.append(ctx.phase)

            bus.subscribe(cb, phase="before")
            bus.subscribe(cb, phase="after")
            bus.emit(_ctx(call_id="1", phase="before"))
            bus.emit(_ctx(call_id="2", phase="after"))
        self.assertEqual(phases, ["before", "after"])

    def test_unsubscribe_removes_callback(self) -> None:
        seen: list[int] = []
        with ObserverBus(max_workers=1) as bus:

            def cb(ctx: ObserverContext) -> None:
                seen.append(1)

            bus.subscribe(cb)
            bus.unsubscribe(cb)
            bus.emit(_ctx())
        self.assertEqual(seen, [])

    def test_callback_decorator_registers(self) -> None:
        seen: list[str] = []
        with ObserverBus(max_workers=1) as bus:

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
        seen: list[int] = []
        with ObserverBus(max_workers=1) as bus:

            @bus.callback(phase="after", method_name="run")
            def cb(_: ObserverContext) -> None:
                seen.append(1)

            bus.emit(
                _ctx(
                    call_id="1",
                    method_name="other",
                    qualname="object.other",
                    phase="after",
                )
            )
            self.assertEqual(seen, [])

            bus.emit(
                _ctx(
                    call_id="2",
                    method_name="run",
                    qualname="object.run",
                    phase="after",
                )
            )
        self.assertEqual(seen, [1])

    def test_callback_decorator_rejects_invalid_filter_keys(self) -> None:
        with ObserverBus(max_workers=1) as bus:
            with self.assertRaises(ValueError) as ar:

                @bus.callback(not_a_context_field=1)
                def cb(ctx: ObserverContext) -> None:
                    pass

            self.assertIn("invalid callback filters", str(ar.exception))

    def test_emit_listener_exception_does_not_propagate(self) -> None:
        log = logging.getLogger("observer.bus")
        prev = log.disabled
        log.disabled = True
        try:
            with ObserverBus(max_workers=1) as bus:

                def bad(_: ObserverContext) -> None:
                    raise RuntimeError("boom")

                bus.subscribe(bad)
                bus.emit(_ctx())
        finally:
            log.disabled = prev

    def test_emit_order_matches_subscription_order(self) -> None:
        order: list[int] = []
        with ObserverBus(max_workers=1) as bus:

            def first(_: ObserverContext) -> None:
                order.append(1)

            def second(_: ObserverContext) -> None:
                order.append(2)

            bus.subscribe(first)
            bus.subscribe(second)
            bus.emit(_ctx())
        self.assertEqual(order, [1, 2])

    def test_async_coroutine_function_callback_runs(self) -> None:
        phases: list[str] = []

        async def acb(ctx: ObserverContext) -> None:
            phases.append(ctx.phase)

        with ObserverBus(max_workers=1) as bus:
            bus.subscribe(acb)
            bus.emit(_ctx(phase="before"))
        self.assertEqual(phases, ["before"])

    def test_async_callable_instance_callback_runs(self) -> None:
        seen: list[str] = []

        class AsyncFn:
            async def __call__(self, ctx: ObserverContext) -> None:
                seen.append(ctx.phase)

        with ObserverBus(max_workers=1) as bus:
            bus.subscribe(AsyncFn())
            bus.emit(_ctx(phase="after"))
        self.assertEqual(seen, ["after"])


class ObserveMethodsTests(unittest.TestCase):
    def test_instance_method_emits_before_and_after(self) -> None:
        phases: list[str] = []
        with ObserverBus(max_workers=1) as bus:
            bus.subscribe(lambda ctx: phases.append(ctx.phase))

            @observe_methods(bus)
            class Svc:
                def add(self, a: int, b: int) -> int:
                    return a + b

            self.assertEqual(Svc().add(1, 2), 3)
        self.assertEqual(phases, ["before", "after"])

    def test_emit_before_false_skips_before_phase(self) -> None:
        phases: list[str] = []
        with ObserverBus(max_workers=1) as bus:
            bus.subscribe(lambda ctx: phases.append(ctx.phase))

            @observe_methods(bus, emit_before=False)
            class Svc:
                def add(self, a: int, b: int) -> int:
                    return a + b

            self.assertEqual(Svc().add(1, 2), 3)
        self.assertEqual(phases, ["after"])

    def test_same_call_id_across_phases_for_sync_call(self) -> None:
        ids: list[str] = []
        with ObserverBus(max_workers=1) as bus:
            bus.subscribe(lambda ctx: ids.append(ctx.call_id))

            @observe_methods(bus)
            class Svc:
                def add(self, a: int, b: int) -> int:
                    return a + b

            Svc().add(1, 2)
        self.assertEqual(len(ids), 2)
        self.assertEqual(ids[0], ids[1])

    def test_error_phase_then_exception_reraised(self) -> None:
        phases: list[str] = []
        with ObserverBus(max_workers=1) as bus:
            bus.subscribe(lambda ctx: phases.append(ctx.phase))

            @observe_methods(bus)
            class Svc:
                def boom(self) -> None:
                    raise ValueError("x")

            with self.assertRaises(ValueError):
                Svc().boom()
        self.assertEqual(phases, ["before", "error"])

    def test_classmethod_context_owner_and_pure_args(self) -> None:
        snapshots: list[tuple[Any, Any, tuple[Any, ...]]] = []
        with ObserverBus(max_workers=1) as bus:

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
        kinds: list[str] = []
        owners: list[Any] = []
        with ObserverBus(max_workers=1) as bus:

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
        with ObserverBus(max_workers=1) as bus:

            @observe_methods(bus)
            class Svc:
                @property
                def x(self) -> int:
                    return 1

            self.assertIsInstance(Svc.x, property)

    def test_private_method_skipped_by_default(self) -> None:
        method_names: list[str] = []
        with ObserverBus(max_workers=1) as bus:
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
        method_names: list[str] = []
        with ObserverBus(max_workers=1) as bus:
            bus.subscribe(lambda ctx: method_names.append(ctx.method_name))

            @observe_methods(bus, include_private=True)
            class Svc:
                def _hidden(self) -> int:
                    return 7

            self.assertEqual(Svc()._hidden(), 7)
        self.assertIn("_hidden", method_names)

    def test_subclass_methods_observed(self) -> None:
        names: list[str] = []
        with ObserverBus(max_workers=1) as bus:
            bus.subscribe(
                lambda ctx: names.append(ctx.method_name) if ctx.phase == "after" else None
            )

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
        cls_names: list[str] = []
        with ObserverBus(max_workers=1) as bus:
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
        phases: list[str] = []
        with ObserverBus(max_workers=1) as bus:
            bus.subscribe(lambda ctx: phases.append(ctx.phase))

            @observe_methods(bus)
            @observe_methods(bus)
            class Svc:
                def run(self) -> int:
                    return 1

            self.assertEqual(Svc().run(), 1)
        self.assertEqual(phases, ["before", "after"])

    def test_bus_observe_delegates_to_observe_methods(self) -> None:
        phases: list[str] = []
        with ObserverBus(max_workers=1) as bus:
            bus.subscribe(lambda ctx: phases.append(ctx.phase))

            @bus.observe()
            class Svc:
                def run(self) -> int:
                    return 5

            self.assertEqual(Svc().run(), 5)
        self.assertEqual(phases, ["before", "after"])


class AsyncObserveMethodsTests(unittest.TestCase):
    def test_async_instance_method_phases(self) -> None:
        phases: list[str] = []
        with ObserverBus(max_workers=1) as bus:
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
        phases: list[str] = []
        with ObserverBus(max_workers=1) as bus:
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
        phases: list[str] = []
        with ObserverBus(max_workers=1) as bus:
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
        log: list[str] = []
        with ObserverBus(max_workers=1) as bus:

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

            _ = Child
        self.assertIn("base_hook", log)


if __name__ == "__main__":
    unittest.main()
