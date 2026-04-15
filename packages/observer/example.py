from observer import ObserverBus, ObserverContext

bus = ObserverBus()


@bus.callback()
def log_all(ctx: ObserverContext) -> None:
    print(
        f"[ALL] {ctx.cls_name}.{ctx.method_name} "
        f"phase={ctx.phase} args={ctx.args} kwargs={ctx.kwargs}"
    )


@bus.callback(cls_name="Demo", phase="after")
def log_demo_after(ctx: ObserverContext) -> None:
    print(
        f"[DEMO AFTER] {ctx.cls_name}.{ctx.method_name} "
        f"result={ctx.result} elapsed={ctx.elapsed:.6f}s"
    )


@bus.callback(method_name="ping", phase="after")
def log_ping(ctx: ObserverContext) -> None:
    print(f"[PING] result={ctx.result}")


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


class ChildDemo(Demo):
    def sub(self, a: int, b: int) -> int:
        return a - b

    def add(self, a: int, b: int) -> int:
        return a + b + 100


d = Demo()
print(d.add(1, 2))
print(Demo.build("x"))
print(Demo.ping("hello"))

child = ChildDemo()
print(child.add(1, 2))
print(child.sub(5, 3))
print(ChildDemo.ping("world"))