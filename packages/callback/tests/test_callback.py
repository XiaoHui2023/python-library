from __future__ import annotations

import asyncio
import threading
import unittest
from typing import ClassVar

from callback import Callback
from callback.registry import CallbackLayers


class _Payload(Callback):
    """测试用载荷：字段顺序与校验由 Pydantic 与 _field_names 共同决定。"""

    order_id: str
    total: int = 0


class _WithPrivate(Callback):
    """下划线前缀名不参与数据字段。"""

    _scratch: int
    visible: int


class _WithClassVar(Callback):
    """ClassVar 不参与实例字段。"""

    tag: ClassVar[str] = "cv"
    value: int


class _Child(_Payload):
    """继承链上的字段应合并进 _field_names。"""

    note: str = ""


class CallbackCoreTests(unittest.TestCase):
    def tearDown(self) -> None:
        Callback.clear_layer_registries()

    def test_trigger_returns_same_instance_handlers_mutate(self) -> None:
        @_Payload.before
        def prep(cb: _Payload) -> None:
            cb.total = 10

        @_Payload
        def mid(cb: _Payload) -> None:
            cb.total += 1

        @_Payload.after
        def fin(cb: _Payload) -> None:
            cb.order_id = cb.order_id + ":done"

        out = _Payload.trigger(order_id="a", total=0)
        self.assertIsInstance(out, _Payload)
        self.assertEqual(out.order_id, "a:done")
        self.assertEqual(out.total, 11)

    def test_class_call_equivalent_to_trigger(self) -> None:
        paid = _Payload(order_id="x", total=3)
        self.assertEqual(paid.order_id, "x")
        self.assertEqual(paid.total, 3)

    def test_layer_order_before_middle_after(self) -> None:
        log: list[str] = []

        @_Payload.before
        def b1(cb: _Payload) -> None:
            log.append("b1")

        @_Payload
        def m1(cb: _Payload) -> None:
            log.append("m1")

        @_Payload.after
        def a1(cb: _Payload) -> None:
            log.append("a1")

        _Payload.trigger(order_id="z", total=0)
        self.assertEqual(log, ["b1", "m1", "a1"])

    def test_whole_tier_finishes_before_next_tier(self) -> None:
        log: list[str] = []

        @_Payload
        def m1(cb: _Payload) -> None:
            log.append("m1-start")
            log.append("m1-end")

        @_Payload
        def m2(cb: _Payload) -> None:
            log.append("m2")

        @_Payload.after
        def a1(cb: _Payload) -> None:
            log.append("after")

        _Payload.trigger(order_id="z", total=0)
        self.assertIn("m1-start", log)
        self.assertIn("m1-end", log)
        self.assertIn("m2", log)
        self.assertLess(log.index("after"), len(log))
        self.assertTrue(all(x != "after" or log[i] == "after" for i, x in enumerate(log)))
        self.assertLess(max(log.index(x) for x in ("m1-end", "m2")), log.index("after"))

    def test_single_callable_arg_registers_middle(self) -> None:
        def handler(cb: _Payload) -> None:
            cb.total = 99

        ref = _Payload(handler)
        self.assertIs(ref, handler)
        out = _Payload.trigger(order_id="q", total=0)
        self.assertEqual(out.total, 99)

    def test_callable_payload_use_keyword_to_trigger(self) -> None:
        class _FnPayload(Callback):
            fn: object

        def inner() -> None:
            pass

        out = _FnPayload.trigger(fn=inner)
        self.assertIs(out.fn, inner)

    def test_duplicate_register_same_layer_once(self) -> None:
        hits: list[int] = []

        def h(cb: _Payload) -> None:
            hits.append(1)

        _Payload.register(h)
        _Payload.register(h)
        _Payload.trigger(order_id="a", total=0)
        self.assertEqual(len(hits), 1)

    def test_same_function_different_layers_each_runs(self) -> None:
        hits: list[str] = []

        def h(cb: _Payload) -> None:
            hits.append("x")

        _Payload.register_before(h)
        _Payload.register(h)
        _Payload.register_after(h)
        _Payload.trigger(order_id="a", total=0)
        self.assertEqual(hits, ["x", "x", "x"])

    def test_unknown_kw_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            _Payload.trigger(order_id="a", total=0, extra=1)
        self.assertIn("未知属性", str(ctx.exception))

    def test_too_many_positional_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            _Payload.trigger("a", 0, "surplus")
        self.assertIn("参数过多", str(ctx.exception))

    def test_base_callback_layers_raises(self) -> None:
        with self.assertRaises(TypeError) as ctx:
            Callback.register(lambda c: None)
        self.assertIn("未挂载分层登记", str(ctx.exception))

    def test_get_all_direct_subclasses_only(self) -> None:
        class _Direct(Callback):
            x: int

        class _Grand(_Direct):
            y: int

        all_cb = Callback.get_all()
        self.assertIn(_Direct, all_cb)
        self.assertNotIn(_Grand, all_cb)
        direct = _Direct.get_all()
        self.assertIn(_Grand, direct)

    def test_clear_layer_registries_clears_handlers(self) -> None:
        log: list[str] = []

        @_Payload
        def h(cb: _Payload) -> None:
            log.append("h")

        _Payload.trigger(order_id="a", total=0)
        self.assertEqual(log, ["h"])

        Callback.clear_layer_registries()
        log.clear()
        _Payload.trigger(order_id="b", total=0)
        self.assertEqual(log, [])

    def test_field_names_exclude_underscore_and_classvar(self) -> None:
        self.assertEqual(_WithPrivate._field_names(), ["visible"])
        self.assertEqual(_WithClassVar._field_names(), ["value"])

    def test_field_names_mro_merge_order(self) -> None:
        self.assertEqual(_Child._field_names(), ["order_id", "total", "note"])

    def test_handler_zero_positional_called_without_payload(self) -> None:
        seen: list[str] = []

        @_Payload
        def h() -> None:
            seen.append("ok")

        _Payload.trigger(order_id="a", total=0)
        self.assertEqual(seen, ["ok"])

    def test_arbitrary_object_field_same_reference(self) -> None:
        class _ObjCb(Callback):
            svc: object

        class Svc:
            pass

        s = Svc()

        @_ObjCb
        def touch(cb: _ObjCb) -> None:
            self.assertIs(cb.svc, s)

        out = _ObjCb.trigger(svc=s)
        self.assertIs(out.svc, s)

    def test_async_handlers_same_layer_concurrent(self) -> None:
        """同层 async 在 asyncio.run 的循环内并发；在无运行中事件循环的线程里调用 trigger。"""

        order: list[str] = []
        err: list[BaseException | None] = [None]

        def run_trigger() -> None:
            try:
                barrier = asyncio.Barrier(2)

                async def a(cb: _Payload) -> None:
                    order.append("a-enter")
                    await barrier.wait()
                    order.append("a-leave")

                async def b(cb: _Payload) -> None:
                    order.append("b-enter")
                    await barrier.wait()
                    order.append("b-leave")

                _Payload.register(a)
                _Payload.register(b)

                @_Payload.after
                def tail(cb: _Payload) -> None:
                    order.append("after")

                _Payload.trigger(order_id="c", total=0)
            except BaseException as e:
                err[0] = e

        th = threading.Thread(target=run_trigger)
        th.start()
        th.join()
        self.assertIsNone(err[0], msg=str(err[0]))
        self.assertIn("a-enter", order)
        self.assertIn("b-enter", order)
        head = order[:2]
        self.assertSetEqual(set(head), {"a-enter", "b-enter"})
        self.assertEqual(order[-1], "after")


class CallbackAsyncTests(unittest.IsolatedAsyncioTestCase):
    def tearDown(self) -> None:
        Callback.clear_layer_registries()

    async def test_trigger_inside_running_loop_raises(self) -> None:
        @_Payload
        def _noop(cb: _Payload) -> None:
            pass

        with self.assertRaises(RuntimeError) as ctx:
            _Payload.trigger(order_id="in-loop", total=0)
        self.assertIn("事件循环", str(ctx.exception))


class CallbackSyncHandlerThreadTests(unittest.TestCase):
    def tearDown(self) -> None:
        Callback.clear_layer_registries()

    def test_sync_handler_runs_off_event_loop_thread(self) -> None:
        main = threading.current_thread()

        @_Payload
        def worker(cb: _Payload) -> None:
            cb.order_id = threading.current_thread().name
            self.assertIsNot(threading.current_thread(), main)

        out = _Payload.trigger(order_id="main", total=0)
        self.assertNotEqual(out.order_id, main.name)


class RegistryLayerTests(unittest.TestCase):
    def test_layer_tier_decorator_returns_callable(self) -> None:
        layers = CallbackLayers()
        called: list[int] = []

        @layers.middle
        def f() -> None:
            called.append(1)

        self.assertIsInstance(layers.middle, type(layers.before))
        f()
        self.assertEqual(called, [1])

    def test_callback_layers_order_and_clear(self) -> None:
        layers = CallbackLayers()
        layers._before.append(lambda: None)
        layers._middle.append(lambda: None)
        layers._after.append(lambda: None)
        self.assertEqual(len(layers.tier_lists_in_order()), 3)
        layers.clear()
        self.assertEqual(layers._before, [])
        self.assertEqual(layers._middle, [])
        self.assertEqual(layers._after, [])


if __name__ == "__main__":
    unittest.main()
