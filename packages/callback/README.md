# callback

**给 Agent 的摘要**：用 `Callback` 子类描述一次调用的**载荷（字段）**；把具体逻辑用装饰器**托管**到注册函数里；`trigger` / `atrigger` 会**等处理函数跑完**再返回**同一个实例**，从上面读被更新后的状态。

## 定位

- 把业务逻辑从调用点**拆出去**，由注册函数在触发时执行。
- **同步** `trigger`：内部用线程池跑各注册函数并 `future.result()`，**阻塞**直到全部结束。
- **异步** `atrigger`：`asyncio.gather` 等待全部协程，需在 async 上下文里 `await`。
- 返回值始终是本次触发的 `Callback` 实例；惯例是在 handler 里**改实例上的字段**作为结果。

## 最小用法

```python
from callback import Callback

class OrderPaid(Callback):
    order_id: str
    amount: int  # handler 里可改写

@OrderPaid
def on_paid(cb: OrderPaid) -> None:
    cb.amount += 1  # 示例：更新状态

cb = OrderPaid.trigger(order_id="a", amount=100)
# cb 即本次载荷；阻塞已结束，可读更新后的字段
assert cb.amount == 101
```

异步回调：子类设 `_async = True`，用 `@Cls` 注册 `async def`，用 `await Cls.atrigger(...)`。

## 规则（实现相关）

- 载荷字段：类体里**类型注解**的普通属性；`ClassVar`、以下划线 `_` 开头的名字**不算**字段。
- 注册：`@MyCallback` 装饰函数；可 `def h(cb: MyCallback)` 或 `def h()`（无参）。
- 同步 / 异步必须一致：同步类不能注册 `async def`；异步类（`_async = True`）不能注册普通 `def`。
- 可重写钩子：`before_trigger` / `after_trigger`（同步），`before_atrigger` / `after_atrigger`（异步）。
- 无注册函数时，`trigger` / `atrigger` 仍会构造并返回实例。