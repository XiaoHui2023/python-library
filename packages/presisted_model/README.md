# python-library-presisted-model

基于 **Pydantic v2** 的小型持久化模型：子类描述字段，通过 `load(path)` 从 JSON 恢复或新建，之后在**字段被赋值**时按防抖策略自动写入磁盘。

**PyPI 安装名（pip）**：`python-library-presisted-model`  
**Python 导入包名**：`presisted_model`

```bash
pip install python-library-presisted-model
```

## 何时会写入文件？

| 行为 | 是否触发落盘 |
|------|----------------|
| 对 **模型字段** 赋值（如 `m.count = 1`） | 是：会 **schedule** 一次防抖写入，在 **连续静止满 `debounce_seconds`** 后写入 **最后一次** 状态 |
| 对 `list` / `dict` 等 **原地修改**（如 `m.items.append(x)`） | **否**（未跟踪原地变更） |
| 以 `_` 开头的名称 | **否**（视为私有，不触发） |
| 进程正常退出 | 已注册的实例会 **尽力** `atexit` 刷盘（将待写入的防抖任务立即落盘，失败则忽略） |

默认 `debounce_seconds=0.5`。短时间多次改同一字段，磁盘上通常只会看到静止后的最终 JSON。  
**无需**也不应依赖任何「手动刷盘」API；若测试或脚本里需要确认文件已写出，在赋值后 `sleep` 略大于 `debounce_seconds` 即可。

## 最小示例

```python
from pathlib import Path
from pydantic import Field
from presisted_model import PresistedModel


class AppState(PresistedModel):
    counter: int = 0
    label: str = Field(default="")


path = Path("state.json")
state = AppState.load(path, debounce_seconds=0.3)
state.counter += 1  # 触发赋值后，静止满 debounce 即落盘
```

## API 要点

- **`PresistedModel.load(path, *, debounce_seconds=0.5, json_indent=2)`**  
  文件存在则 `model_validate_json`；不存在则用默认值构造；随后绑定路径并启用防抖持久化。
- **存储格式**：`model_dump_json` 写入目标路径，写文件为 **原子替换**（临时文件再 `replace`）。

## 依赖

- Python ≥ 3.10  
- `pydantic >= 2`

---

**For AI agents / tooling**: After `pip install python-library-presisted-model`, import `PresistedModel` from `presisted_model`. Persistence is **debounced** on **Pydantic field assignment** only; **in-place** mutations on nested mutable values are **not** auto-saved. Rely on **`debounce_seconds`** and **process exit** for durability; there is **no public flush API**.
