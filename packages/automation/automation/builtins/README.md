# Builtins

`builtins` 提供了当前包内置的可直接使用的类型。

目前包含：

- Action
  - `call_entity_method`
- Condition
  - `expression`

这些类型会在导入 `automation` 时自动注册，因此可以直接在配置中使用对应的 `type`。

## 当前内置 Action

- [call_entity_method](./action/README.md)

## 当前内置 Condition

- [expression](./condition/README.md)

## 什么时候用 builtins

如果你的需求只是：

- 调用某个实体的方法
- 根据条件结果和实体属性做布尔表达式判断

那么直接使用 builtins 就够了，不需要自己再写子类。

## 什么时候自定义类型

如果你需要：

- 更复杂的事件源
- 自定义动作执行逻辑
- 更特殊的条件判断方式
- 更强的实体行为封装

就应该继承 `core` 里的抽象类自己扩展。
