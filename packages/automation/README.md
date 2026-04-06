## Builder 用法

`builder` 用于根据配置批量创建 `entities`、`events`、`conditions`、`actions` 和 `triggers`。

它的约定是：

- 一级 key 表示模块分类：`entities`、`events`、`conditions`、`actions`、`triggers`
- 二级 key 表示实例名，用于保证同一分类下名称唯一
- 每个实例配置中必须包含 `type`
- `type` 用于从对应的 registry 中查找已注册的类
- 剩余字段会作为构造参数传给对应类

### 配置示例

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

events: {}

conditions: {}

triggers: {}
```