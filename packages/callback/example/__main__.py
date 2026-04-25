from __future__ import annotations

import asyncio
import sys
import time
from collections.abc import Callable
from typing import ClassVar

from callback import AsyncCallback, Callback


class Checkout(Callback):
    """模块级子类：展示 @before、中间、@after 与多种触发写法。"""

    order_id: str
    total: int = 0
    lines: ClassVar[list[str]] = []


@Checkout.before
def prepare(cb: Checkout) -> None:
    """前层：与 Checkout.register_before 同一套登记规则。"""
    Checkout.lines.append(f"before:{cb.order_id}")


@Checkout
def add_fee(cb: Checkout) -> None:
    """中间层：等价于 Checkout.register(fn) 或把函数交给 `Checkout(fn)` 单参登记。"""
    cb.total += 3


@Checkout.after
def finalize(cb: Checkout) -> None:
    """后层：与 Checkout.register_after 相同。"""
    Checkout.lines.append(f"after:total={cb.total}")


def demo_checkout_triggers() -> None:
    """`trigger` 与 `子类(...)` 等价；支持关键字与位置参数。"""
    Checkout.lines.clear()

    a = Checkout.trigger(order_id="A", total=10)
    b = Checkout("B", 5)

    print("--- Checkout：before / 中间 / after + trigger 与构造调用 ---")
    print("a:", a.order_id, a.total, "| b:", b.order_id, b.total)
    print("lines:", Checkout.lines)


def demo_explicit_register() -> None:
    """register_before / register / register_after 与三层装饰器等价。"""

    class Shipment(Callback):
        code: str

    def pre(cb: Shipment) -> None:
        steps.append("reg:before")

    def mid(cb: Shipment) -> None:
        steps.append(f"reg:middle:{cb.code}")

    def post(cb: Shipment) -> None:
        steps.append("reg:after")

    steps: list[str] = []
    Shipment.register_before(pre)
    Shipment.register(mid)
    Shipment.register_after(post)
    Shipment.trigger(code="X1")

    print("--- 仅用 register_before / register / register_after ---")
    print("steps:", steps)


def demo_middle_class_call_register() -> None:
    """`子类(可调用对象)` 单参且无 kwargs → 向中间层登记，等价于 register。"""

    class Ping(Callback):
        n: int = 0

    def bump(cb: Ping) -> None:
        cb.n += 100

    Ping(bump)
    p = Ping()
    print("--- 中间层简便写法：Ping(bump) 再 Ping() ---")
    print("n =", p.n)


def demo_async_same_tier() -> None:
    """同层多 async 在 AsyncCallback 上并发，三层仍 前→中→后。"""

    class TaskBatch(AsyncCallback):
        name: str

    trace: list[str] = []

    async def run_demo() -> None:
        @TaskBatch.before
        async def b1(cb: TaskBatch) -> None:
            await asyncio.sleep(0.02)
            trace.append("before")

        @TaskBatch
        async def m1(cb: TaskBatch) -> None:
            await asyncio.sleep(0.02)
            trace.append("mid1")

        @TaskBatch
        async def m2(cb: TaskBatch) -> None:
            await asyncio.sleep(0.02)
            trace.append("mid2")

        @TaskBatch.after
        async def tail(cb: TaskBatch) -> None:
            trace.append(f"after:{cb.name}")

        trace.clear()
        t0 = time.perf_counter()
        await TaskBatch(name="job")
        dt = time.perf_counter() - t0
        print("--- 同层 async 并发（中层两路 sleep 远短于串行 0.08s）---")
        print(f"elapsed≈{dt:.3f}s, trace:", trace)

    asyncio.run(run_demo())


def demo_callable_field_use_keyword() -> None:
    """若误写 `Payload(fn)` 且 fn 可调用，会被当成中间层登记而非触发；应用关键字传参。"""

    class Payload(Callback):
        fn: Callable[[], None]
        tag: str = "ok"

    trail: list[str] = []

    @Payload
    def run(cb: Payload) -> None:
        cb.fn()
        trail.append(cb.tag)

    trail.clear()

    def side() -> None:
        trail.append("side")

    Payload(fn=side, tag="via-kw")
    print("--- 载荷含可调用对象：使用 Payload(fn=..., tag=...) 触发 ---")
    print("trail:", trail)


def demo_zero_arg_handler() -> None:
    """签名无参数时，库会不带载荷调用。"""

    class Signal(Callback):
        flag: int = 0

    hits: list[str] = []

    @Signal.after
    def ping() -> None:
        hits.append("ping")

    hits.clear()
    Signal()
    print("--- 无参 after 处理函数 ---")
    print("hits:", hits)


def demo_same_handler_registered_twice() -> None:
    """同一函数对象在同一层登记多次，触发时仍只执行一次。"""

    class Dup(Callback):
        x: int = 0

    counts: list[int] = []

    def once(cb: Dup) -> None:
        counts.append(len(counts) + 1)
        cb.x += 1

    Dup.register(once)
    Dup.register(once)
    inst = Dup()
    print("--- 同层重复 register 同一函数 → 只跑一次 ---")
    print("counts:", counts, "x:", inst.x)


def main() -> None:
    """按段打印，涵盖 before/after、register* 与常用简写。"""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except OSError:
            pass

    demo_callable_field_use_keyword()
    demo_zero_arg_handler()
    demo_middle_class_call_register()
    demo_async_same_tier()
    demo_explicit_register()
    demo_same_handler_registered_twice()
    demo_checkout_triggers()


if __name__ == "__main__":
    main()
