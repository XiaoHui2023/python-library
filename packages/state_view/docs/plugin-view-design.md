# state_view 插件协作设计

## 定位

`state_view` 是一个轻量 Python 基础库，用来把 Python 数据结构实例暴露成前端可读写的数据状态。

库本身不依赖 FastAPI、Flask、React 或 Vite。它只规定 Python 对象如何导出数据、如何接收前端修改、如何描述可编辑字段。HTTP 路由、React 组件加载、插件目录扫描由宿主项目完成。

## 角色

+ **Python 数据实例**：保存真实状态，字段可读写，`property` 可提供计算值。
+ **StateView**：包住一个 Python 数据实例，提供 `get()`、`set()`、`schema()` 等基础方法。
+ **宿主项目**：把 `StateView` 挂到 FastAPI、Flask、WebSocket、SSE 或其它传输方式上。
+ **外部插件**：同时提供 Python 状态脚本和 React 组件资源。
+ **React 组件**：动态加载后显示数据，用户编辑时把修改提交给宿主项目。

## 基础接口

最小接口只需要三个方法：

```python
view = StateView(obj)

data = view.get()
data = view.set({"seed": 123})
schema = view.schema()
```

+ `get()` 返回当前完整数据，包含普通字段和计算属性。
+ `set(patch)` 根据前端提交的字段修改实例，修改后返回新的完整数据。
+ `schema()` 返回字段说明，前端可据此知道哪些字段可编辑、哪些字段只读、哪些字段是枚举。

`StateView` 不负责 HTTP。FastAPI 路由只是外部使用方式：

```python
@app.get("/api/plugins/{name}/data")
def get_data(name: str):
    return plugin_views[name].get()

@app.post("/api/plugins/{name}/data")
def set_data(name: str, patch: dict):
    return plugin_views[name].set(patch)

@app.get("/api/plugins/{name}/schema")
def get_schema(name: str):
    return plugin_views[name].schema()
```

## Python 数据结构

插件作者可以使用普通类、`dataclass`、`Enum` 和 `property`。基础库不强制使用 Pydantic。

```python
from dataclasses import dataclass, field
from enum import Enum


class CaseName(str, Enum):
    smoke = "smoke"
    regression = "regression"


@dataclass
class CaseConfig:
    name: CaseName
    enabled: bool = True
    count: int = 1


@dataclass
class RunState:
    name: str
    project: str
    seed: int = 1
    cases: list[CaseConfig] = field(default_factory=list)

    @property
    def total_runs(self) -> int:
        return sum(case.count for case in self.cases if case.enabled)
```

`get()` 返回可传输数据：

```json
{
  "name": "demo",
  "project": "alpha",
  "seed": 1,
  "cases": [
    {
      "name": "smoke",
      "enabled": true,
      "count": 1
    }
  ],
  "total_runs": 1
}
```

`set()` 接收前端修改：

```json
{
  "seed": 123,
  "cases": [
    {
      "name": "smoke",
      "enabled": true,
      "count": 5
    }
  ]
}
```

修改后，`total_runs` 等计算属性由 Python 重新计算。

## 字段规则

| 字段来源 | 前端行为 |
| --- | --- |
| 普通字段 | 可读；是否可写由 `StateView` 配置决定 |
| `property` | 只读；每次 `get()` 时重新计算 |
| `Enum` | 导出枚举值；`schema()` 中列出可选项 |
| 嵌套 dataclass | 递归导出对象 |
| list / dict | 转成 JSON 可传输结构 |

字段写入默认走 `setattr`。如果某个字段不允许前端修改，应在 `StateView` 配置中声明为只读。

```python
view = StateView(
    state,
    editable=["seed", "cases"],
    readonly=["name", "project", "total_runs"],
)
```

## 插件目录

宿主项目可以约定外部插件目录。插件不需要和主项目源码放在一起。

```text
plugins/
  run_panel/
    plugin.json
    python/
      run_state.py
    frontend/
      dist/
        index.js
        style.css
```

`plugin.json` 说明 Python 状态类和 React 组件资源：

```json
{
  "name": "run_panel",
  "python": {
    "file": "python/run_state.py",
    "class": "RunState",
    "factory": "create_state"
  },
  "frontend": {
    "module": "frontend/dist/index.js",
    "export": "RunPanel",
    "style": "frontend/dist/style.css"
  }
}
```

Python 插件可以提供工厂函数：

```python
def create_state():
    return RunState(
        name="demo",
        project="alpha",
        cases=[CaseConfig(name=CaseName.smoke)]
    )
```

宿主项目负责读取 `plugin.json`、动态导入 Python 文件、创建状态实例，再用 `StateView` 包装该实例。

## React 插件

React 插件构建成浏览器可加载的 ES Module。宿主前端根据插件信息动态导入：

```ts
const mod = await import("/plugins/run_panel/frontend/dist/index.js");
const Component = mod.RunPanel;
```

组件接收宿主传入的状态和操作函数：

```tsx
export function RunPanel({ data, schema, set, refresh }) {
  return (
    <section>
      <h2>{data.project} / {data.name}</h2>

      <input
        value={data.seed}
        onChange={(event) => set({ seed: Number(event.target.value) })}
      />

      <div>Total runs: {data.total_runs}</div>

      <button onClick={refresh}>Refresh</button>
    </section>
  );
}
```

React 组件可以自由使用 MUI、Ant Design、Mantine、Radix UI 或自己的样式。Python 基础库不关心前端实现。

## API 交互

宿主项目推荐提供以下 API：

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| `GET` | `/api/plugins` | 返回插件列表 |
| `GET` | `/api/plugins/{name}/schema` | 返回字段说明 |
| `GET` | `/api/plugins/{name}/data` | 返回当前数据 |
| `POST` | `/api/plugins/{name}/data` | 提交字段修改，返回新数据 |
| `POST` | `/api/plugins/{name}/action/{action}` | 可选；触发 Python 动作 |
| `GET` | `/api/plugins/{name}/events` | 可选；推送任务状态、日志或进度 |

普通编辑流程：

1. React 调用 `GET /data` 获取当前数据。
2. 用户编辑输入框、下拉框或列表。
3. React 调用 `POST /data` 提交 patch。
4. Python `StateView.set()` 修改实例。
5. Python 返回新的完整数据。
6. React 使用新数据重绘组件。

后端主动变化时，前端可以用轮询、SSE 或 WebSocket 获取新数据。基础库只提供 `get()`，不绑定传输方式。

## 数据与计算

业务计算留在 Python 数据实例中。React 组件只展示结果、收集用户输入和触发动作。

适合放在 Python 中的内容：

+ 根据 seed、case、count 计算总运行次数。
+ 根据字段组合生成命令字符串。
+ 根据任务状态计算展示状态。
+ 根据外部文件或进程刷新数据。
+ 校验前端提交的字段。

适合放在 React 中的内容：

+ 布局、颜色、图案、折叠区域。
+ 输入框、下拉框、按钮和列表交互。
+ 局部动画和组件样式。
+ 调用 `set()`、`refresh()` 和动作函数。

## 安全边界

外部插件包含可执行 Python 和 JavaScript，只适合加载可信插件。

宿主项目应至少做这些限制：

+ 插件目录由用户显式指定。
+ Python 动态导入前读取 `plugin.json`。
+ `set()` 只允许修改声明为可编辑的字段。
+ `property` 和只读字段不能由前端写入。
+ React 插件资源只从已加载插件目录提供。
+ 动作 API 需要明确列出可调用动作。

## 推荐项目结构

```text
packages/state_view/
  state_view/
    __init__.py
    view.py          # StateView
    fields.py        # 字段扫描、枚举、只读/可写说明
    convert.py       # Python 对象与 JSON 数据互转
    patch.py         # set() 写入规则
  docs/
    plugin-view-design.md
  examples/
    fastapi_host/
      app.py
      plugins/
        run_panel/
          plugin.json
          python/
            run_state.py
          frontend/
            dist/
              index.js
              style.css
```

`state_view` 只实现 Python 对象到可传输数据的转换和写入规则。`examples/fastapi_host` 展示如何把它接到 FastAPI 和 React 插件。

## 实现边界

基础库应保持很薄：

+ 不依赖 FastAPI。
+ 不依赖 React。
+ 不启动 HTTP 服务。
+ 不扫描固定插件目录。
+ 不构建前端资源。
+ 不执行前端代码。

基础库应提供：

+ `StateView(obj)`。
+ `get()`。
+ `set(patch)`。
+ `schema()`。
+ 普通字段、枚举、嵌套对象、列表、字典、`property` 的导出规则。
+ 可编辑字段和只读字段控制。
+ 简单、明确的错误信息。

宿主项目应负责：

+ 插件目录扫描。
+ Python 动态导入。
+ FastAPI 路由。
+ React 静态资源托管。
+ 前端 ES Module 动态导入。
+ SSE、WebSocket 或轮询刷新。
