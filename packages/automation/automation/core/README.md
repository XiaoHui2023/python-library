# Core

`core` 定义了自动化系统的五类核心抽象：

- `Entity`
- `Event`
- `Condition`
- `Action`
- `Trigger`

## 关系图

```text
Event --> Trigger --> Condition(s) --> Action(s)
                      ^
                      |
                   Entity
```

更准确地说：

- `Trigger` 监听某个 `Event`
- `Trigger` 在运行时会检查一组 `Condition`
- 所有条件通过后，`Trigger` 会执行一组 `Action`
- `Condition` 和 `Action` 通常会读取或操作 `Entity`

## BaseAutomation

所有核心类型都继承自 `BaseAutomation`。

它提供了：

- `instance_name`：实例名
- 子类注册机制
- `validate(ctx)`：校验配置、解析引用，但不做副作用
- `activate(ctx)`：在全部校验通过后执行绑定、副作用注册

推荐约定：

- `validate(ctx)` 里只做检查和引用解析
- `activate(ctx)` 里再做事件绑定等副作用操作

## Entity

`Entity` 表示业务实体实例，例如：

- 路由器
- 灯
- 传感器
- 开关
- 用户定义的设备对象

实体通常承载状态和可调用的方法。

示例：

```python
from typing import ClassVar

from automation import Entity


class HomeRouter(Entity):
    _type: ClassVar[str] = "home_router"

    hostname: str
    username: str
    password: str

    def reboot(self) -> None:
        ...
```

## Event

`Event` 表示触发源。

它负责：

- 注册触发回调
- 在 `fire()` 时触发这些回调

示例：

```python
from typing import ClassVar

from automation import Event


class SimpleEvent(Event):
    _type: ClassVar[str] = "simple_event"
```

## Condition

`Condition` 表示条件判断。

它需要实现：

- `check() -> bool`

示例：

```python
from typing import ClassVar

from automation import Condition


class AlwaysTrue(Condition):
    _type: ClassVar[str] = "always_true"

    def check(self) -> bool:
        return True
```

## Action

`Action` 表示动作。

它需要实现：

- `run()`

示例：

```python
from typing import ClassVar

from automation import Action


class PrintAction(Action):
    _type: ClassVar[str] = "print_action"

    message: str

    async def run(self):
        print(self.message)
```

## Trigger

`Trigger` 负责把事件、条件、动作关联起来。

它会：

1. 引用一个 `event`
2. 引用零个或多个 `conditions`
3. 引用一个或多个 `actions`
4. 在事件触发时按顺序执行条件判断和动作

示例：

```python
from typing import ClassVar

from automation import Trigger


class SimpleTrigger(Trigger):
    _type: ClassVar[str] = "simple_trigger"
```

## `type` 和实例名的区别

这是最容易混淆的地方。

### `type`

`type` 是“类型名”，用于找到具体类，例如：

- `home_router`
- `simple_event`
- `call_entity_method`
- `expression`

### 实例名

实例名是配置里的二级 key，例如：

- `router_1`
- `manual_reboot`
- `router_online`
- `reboot_router`

例如：

```yaml
entities:
  router_1:
    type: home_router
```

这里：

- `router_1` 是实例名
- `home_router` 是类型名

## 生命周期

推荐把对象生命周期理解为两阶段：

1. `build`
2. `validate / activate`

### build

`builder` 根据配置创建实例对象。

### validate

检查配置是否合法，并解析实例之间的引用关系。

### activate

在所有对象都校验通过后，再执行副作用，例如把 `Trigger.run` 订阅到 `Event` 上。

这种拆分可以避免构建失败时留下半初始化状态。
