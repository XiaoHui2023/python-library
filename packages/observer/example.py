import asyncio
import logging

from observer import ObserverBus, ObserverContext


logging.basicConfig(level=logging.INFO)

bus = ObserverBus()


@bus.callback()
def log_all(ctx: ObserverContext) -> None:
    print(
        f"[ALL] {ctx.cls_name}.{ctx.method_name} "
        f"phase={ctx.phase} args={ctx.args} kwargs={ctx.kwargs}"
    )


@bus.callback(cls_name="Demo", phase="after")
async def log_demo_after(ctx: ObserverContext) -> None:
    await asyncio.sleep(0.01)
    print(
        f"[DEMO AFTER] {ctx.cls_name}.{ctx.method_name} "
        f"result={ctx.result} elapsed={ctx.elapsed:.6f}s"
    )


@bus.callback(method_name="ping", phase="after")
def log_ping(ctx: ObserverContext) -> None:
    print(f"[PING] result={ctx.result}")


@bus.callback(method_name="add", phase="after")
def broken_callback(ctx: ObserverContext) -> None:
    raise RuntimeError("callback boom")


@bus.observe()
class Demo:
    def add(self, a: int, b: int) -> int:
        return a + b

    @classmethod
    def build(cls, name: str) -> "Demo":
        return cls()

    @staticmethod
    def ping(msg: str) -> str:
        return f"pong:{msg}"

    async def async_add(self, a: int, b: int) -> int:
        await asyncio.sleep(0.01)
        return a + b


class ChildDemo(Demo):
    def sub(self, a: int, b: int) -> int:
        return a - b

    def add(self, a: int, b: int) -> int:
        return a + b + 100


async def main() -> None:
    d = Demo()
    print(d.add(1, 2))
    print(Demo.build("x"))
    print(Demo.ping("hello"))
    print(await d.async_add(3, 4))

    child = ChildDemo()
    print(child.add(1, 2))
    print(child.sub(5, 3))
    print(ChildDemo.ping("world"))


asyncio.run(main())
bus.close(wait=True)