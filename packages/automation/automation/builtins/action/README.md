# call_entity_method

`call_entity_method` 是一个内置 `Action`，用于调用某个实体实例上的方法。

## 作用

当触发器决定执行这个动作时，它会：

1. 找到指定的实体实例
2. 找到该实体上的目标方法
3. 用 `args` 里的关键字参数调用这个方法
4. 如果方法返回可等待对象，则等待其完成

## 配置格式

```yaml
actions:
  action_name:
    type: call_entity_method
    entity: entity_name
    method: method_name
    args: {}
```

## 参数说明

- `entity`：实体实例名，必须在 `entities` 中存在
- `method`：要调用的方法名
- `args`：方法调用时使用的关键字参数字典

## 示例 1：无参数方法

```yaml
actions:
  reboot_router:
    type: call_entity_method
    entity: router_1
    method: reboot
    args: {}
```

等价语义：

```python
router_1.reboot()
```

## 示例 2：带参数方法

```yaml
actions:
  set_wifi:
    type: call_entity_method
    entity: router_1
    method: set_wifi
    args:
      ssid: MyWiFi
      password: 12345678
```

等价语义：

```python
router_1.set_wifi(ssid="MyWiFi", password="12345678")
```

## 校验规则

在构建阶段会检查：

- `entity` 引用的实体是否存在
- 目标方法是否存在
- 目标属性是否可调用
- `args` 是否能绑定到方法签名

如果校验失败，会在构建时抛错，而不是等到运行时才发现。

## 适用场景

适合以下场景：

- 打开/关闭设备
- 发送命令到实体
- 调用同步或异步实体方法
- 用配置驱动实体行为
