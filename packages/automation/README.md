# automation

`automation` 是一个轻量的自动化规则引擎骨架，用配置把 `entities`、`events`、`conditions`、`actions`、`triggers` 组装起来，形成一条规则链路：

`event` 触发 -> 检查 `conditions` -> 执行 `actions`

## 文档导航

- [核心概念](./automation/core/README.md)
- [内置类型总览](./automation/builtins/README.md)
- [内置 Action：call_entity_method](./automation/builtins/action/README.md)
- [内置 Condition：expression](./automation/builtins/condition/README.md)

## Builder 用法

`automation.builder` 用于根据配置批量创建 `entities`、`events`、`conditions`、`actions` 和 `triggers`。

配置约定：

- 一级 key 表示模块分类：`entities`、`events`、`conditions`、`actions`、`triggers`
- 二级 key 表示实例名，用于保证同一分类下名称唯一
- 每个实例配置中必须包含 `type`
- `type` 用于从对应 registry 中查找已注册的类
- 除 `type` 外的字段会作为构造参数传给对应类型

## 五类对象的职责

- `entities`：业务实体实例，例如路由器、灯、传感器、设备等
- `events`：事件源，用于触发自动化流程
- `conditions`：条件判断，决定是否继续执行
- `actions`：动作，表示触发后要执行的操作
- `triggers`：把 `event`、`conditions`、`actions` 绑定起来

可以把它理解为：

1. 定义实体
2. 定义事件
3. 定义条件
4. 定义动作
5. 用触发器把它们串起来

## 最小心智模型

如果有下面这段配置：

```yaml
entities:
  router_1:
    type: home_router
    hostname: 192.168.0.1
    username: admin
    password: admin

actions:
  reboot_router:
    type: call_entity_method
    entity: router_1
    method: reboot
    args: {}
```

它表达的是：

- 创建一个实体实例 `router_1`
- 这个实体的具体实现类型是 `home_router`
- 创建一个动作实例 `reboot_router`
- 这个动作的实现类型是 `call_entity_method`
- 这个动作会调用 `router_1.reboot()`

也就是把下面这类代码配置化：

```python
router_1.reboot()
```

## 完整配置示例

```yaml
entities:
  router_1:
    type: home_router
    hostname: 192.168.0.1
    username: admin
    password: admin

events:
  manual_reboot:
    type: simple_event

conditions:
  router_online:
    type: expression
    expr: "{router_1.status.online} == True"

actions:
  reboot_router:
    type: call_entity_method
    entity: router_1
    method: reboot
    args: {}

triggers:
  reboot_when_manual_event:
    type: simple_trigger
    event: manual_reboot
    conditions:
      - router_online
    actions:
      - reboot_router
```

这个例子的含义是：

1. 创建一个名为 `router_1` 的实体
2. 创建一个名为 `manual_reboot` 的事件
3. 创建一个条件 `router_online`
4. 创建一个动作 `reboot_router`
5. 创建一个触发器 `reboot_when_manual_event`
6. 当 `manual_reboot` 触发时，先检查 `router_online`，条件成立后再执行 `reboot_router`

## 字段含义

### 所有 section 的公共规则

- 二级 key 是实例名，例如 `router_1`、`reboot_router`
- `type` 是类型名，不是 Python 类名
- 除了 `type` 之外的字段都会传给对应类型的构造函数

### `triggers`

- `event`：事件实例名，引用 `events` 中定义的对象
- `conditions`：条件实例名列表，引用 `conditions`
- `actions`：动作实例名列表，引用 `actions`

### `actions.call_entity_method`

- `entity`：实体实例名
- `method`：实体方法名
- `args`：传给该方法的关键字参数字典

### `conditions.expression`

- `expr`：表达式字符串
- `{condition_name}` 表示引用另一个条件的布尔结果
- `{实体名.属性路径}` 表示读取实体属性
- 表达式结果必须是 `bool`

## 快速开始

如果你只想快速理解这套系统，建议按这个顺序阅读：

1. 先看 [核心概念](./automation/core/README.md)
2. 再看 [内置类型总览](./automation/builtins/README.md)
3. 然后重点看 [call_entity_method](./automation/builtins/action/README.md) 和 [expression](./automation/builtins/condition/README.md)
4. 最后回到上面的完整配置示例，对照理解配置如何落到运行行为

## 扩展方式

你可以继承核心抽象类来自定义自己的类型：

- `Entity`
- `Event`
- `Condition`
- `Action`
- `Trigger`

定义后会注册到对应 registry 中，供 `builder` 通过 `type` 查找并实例化。

更详细的抽象层说明见 [核心概念](./automation/core/README.md)。
