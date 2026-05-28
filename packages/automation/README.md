# automation

用 `Automation` 定义一类可触发的异步自动化，再用注册函数接收同一种数据结构。

## Automation 子类

定义自动化时先写数据结构，再派生 `Automation[Payload]`。常用可重载方法：

- `on_build()`：启动时做一次准备。
- `should_run()`：每次触发前判断要不要执行。
- `on_tick()`：运行时按 `interval` 周期调用。

```python
from dataclasses import dataclass

from automation import Automation


@dataclass
class LanPayload:
    mac: str
    ip: str


class LanOnline(Automation[LanPayload]):
    interval: float = 5.0

    async def on_build(self) -> None:
        ...

    async def should_run(self) -> bool:
        return True

    async def on_tick(self) -> None:
        payload = LanPayload(mac="aa:bb:cc", ip="192.168.1.10")
        await self.run(payload)


lan_online = LanOnline(name="lan_online", mode="skip")
```

## 注册函数

自动化实例可以用 `register` 注册异步函数，也可以直接当装饰器用。函数只接收 payload。

```python
@lan_online.register
async def print_lan(payload: LanPayload) -> None:
    print(payload.ip)


@lan_online
async def sync_lan(payload: LanPayload) -> None:
    ...
```

同一次触发会并行执行已注册函数。某个函数报错时会写日志，不影响其它函数继续运行。

## 运行方式

`run()` 会启动运行时并在退出时清理；需要从其它协程或信号里结束时，用 `start()` / `stop()`。

```python
import asyncio

from automation import run


async def main() -> None:
    await run()


asyncio.run(main())
```

```python
import asyncio

from automation import start, stop


async def main() -> None:
    task = asyncio.create_task(start())
    try:
        ...
    finally:
        await stop()
        await task


asyncio.run(main())
```
