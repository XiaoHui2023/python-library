# expression

`expression` 是一个内置 `Condition`，用于通过表达式组合条件结果和实体属性，并返回布尔值。

## 作用

它允许你在配置里直接写条件判断，而不用每次都手写一个新的 `Condition` 子类。

## 配置格式

```yaml
conditions:
  condition_name:
    type: expression
    expr: "{condition_name} and {entity.attr} == True"
```

## 参数说明

- `expr`：表达式字符串
- 表达式中可以使用 `{condition_name}` 引用另一个条件的布尔结果
- 表达式中可以使用 `{实体名.属性路径}` 访问实体属性
- 表达式计算结果必须是 `bool`

## 占位符语法

表达式里的变量可以写成两种形式：

```text
{条件名}
{实体名.属性}
{实体名.属性.子属性}
```

例如：

- `{is_online}`
- `{load_ok}`
- `{router_1.online}`
- `{router_1.status.online}`
- `{lamp.power}`
- `{sensor_1.value}`

## 示例 1：简单布尔判断

```yaml
conditions:
  router_online:
    type: expression
    expr: "{router_1.status.online} == True"
```

## 示例 2：数值比较

```yaml
conditions:
  load_ok:
    type: expression
    expr: "{router_1.load} < 0.8"
```

## 示例 3：引用其他条件

```yaml
conditions:
  is_online:
    type: expression
    expr: "{router_1.status.online} == True"

  load_ok:
    type: expression
    expr: "{router_1.load} < 0.8"

  can_reboot:
    type: expression
    expr: "{is_online} and {load_ok}"
```

## 校验规则

在构建阶段会检查：

- 表达式语法是否合法
- 占位符是否符合 `{条件名}` 或 `{实体名.属性路径}` 形式
- 被引用的条件是否存在
- 被引用的实体是否存在
- 属性路径是否存在
- AST 是否只包含允许的语法节点

在运行阶段会继续检查：

- 表达式求值结果是否为 `bool`
- 条件之间是否存在循环依赖

## 注意事项

- 结果必须是 `bool`
- 不要把它当成通用脚本执行器
- 它更适合做简单、明确、可读的条件判断
- 如果表达式已经变得很长，建议改成自定义 `Condition` 子类

## 推荐使用方式

适合这种“组合条件结果和实体状态”的场景：

- 设备是否在线
- 温度是否超过阈值
- 某个模式是否开启
- 某个值是否落在允许范围内
