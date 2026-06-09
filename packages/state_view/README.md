# state_view

轻量 Python 基础库：把数据类实例暴露成前端可读写的 **data + schema**，经 `set(patch)` 写回 Python；不绑定 HTTP 或 React。

- 独立包：`python-library-state-view`（pip）/ `state_view`（import）
- 框架设计与插件约定：[docs/plugin-view-design.md](docs/plugin-view-design.md)

## 设计特性

### StateView 三方法

`StateView(obj)` 提供 `get()`（含 `property` 计算值）、`set(patch)`（按可编辑规则写回并返回新 data）、`schema()`（字段类型与可编辑说明）。宿主项目把三者挂到 REST、WebSocket 等传输层即可。

### 数据结构

插件作者可用 `dataclass`、`Enum`、`property` 与普通 list/dict；库不强制 Pydantic。嵌套对象与枚举在导出与 schema 中递归处理。

### 实现边界

核心包只做对象与 JSON 互转、字段扫描与写入规则；插件目录、`plugin.json`、FastAPI 路由、React ES Module 加载由宿主与 `examples/` 承担。

## 配置

`StateView` 构造时可声明 `editable` / `readonly` 字段列表；`property` 与只读字段拒绝前端写入。细则见设计文档「字段规则」一节。
