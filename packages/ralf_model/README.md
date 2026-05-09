# ralf_model

在 **RALF（Register Abstraction Layer Format）源文本** 与 **`RalfDocument` / 抽象节点类型**（`BlockNode`、`RegisterNode`、`FieldNode`，并实现 `AbstractRalf*`）之间做解析与生成。

## 用法

```python
from pathlib import Path

from ralf_model import dump_ralf, load_ralf_file, parse_ralf

doc = parse_ralf(Path("chip.ralf").read_text(encoding="utf-8"))
text = dump_ralf(doc)
```

亦可使用 `loads_ralf` / `dumps_ralf`、`load_ralf_file` / `dump_ralf_file`（见 `ralf_model.io`）。加载时可传入 **`include_paths`**（类似 ``ralgen -I dir``），配合 **`source`** 行递归展开后再解析；相对路径先相对**当前文件目录**，再依次在各 include 目录检索。

### source 与 include

RALF 常作为 Tcl 脚本。单独成行的 ``source "f.ralf"``、``source {path}``、``source name.ralf``（可有行尾 ``;``、``#`` 注释）会在解析前被展开。不需要展开时：`loads_ralf(..., expand_source=False)` 或 `load_ralf_file(..., expand_source=False)`。

```python
from pathlib import Path
from ralf_model import load_ralf_file

doc = load_ralf_file(
    "top.ralf",
    include_paths=[Path("ralf_inc"), Path("../shared")],
)
```

也可直接使用 ``expand_ralf_sources``、``resolve_source_path``（见 `ralf_model.source_expand`）。

## 能力范围

- **block**：定义 ``block 名 { ... }``；简单映射 ``block 名 @地址;``；赋值与可选路径、地址 ``block 左名 = 右名``、``block 左名 = 右名 (hdl路径)``、``... @地址``，可与 ``{ ... }`` 组合。
- `field` 花括号内按**源顺序**保留各条语句（含 `enum { ... };` 等），便于往返。
- `@` 后的偏移在写出时统一为 Verilog 风格十六进制字面量（如 `'h5`）；`bytes` 等为十进制。

与 Synopsys `ralgen` 全语法并非字节级兼容；复杂构造若解析失败可再扩展解析器。
