# configlib

## 变量

所有格式都支持 `${}`：

| 语法 | 含义 |
| --- | --- |
| `${app.name}` | 从配置根部读取路径 |
| `${items.0.id}` | 读取列表里的元素 |
| `${..name}` | 读取当前 mapping 内的相对路径 |
| `${env:PORT}` | 读取环境变量 |
| `${env:PORT:8080}` | 环境变量不存在时使用默认值 |
| `${PORT}` | 配置里没有单级键时，回退到同名环境变量 |

## JSON

支持的后缀：

- `.json`
- `.json5`

## YAML

支持的后缀：

- `.yaml`
- `.yml`

### 导入

```yaml
root: !include app.yaml

app:
  base: !include base.yaml
  json_data: !include data.json5
  toml_data: !include data.toml
  csv_data: !include data.csv

items:
  - !include item.yaml
```

### 列表展开

`${shared}` 独占一行并且同级存在 `-` 项时，引用结果会展开进当前列表。引用值必须是列表。

```yaml
shared: [a, b]

items:
  - head
  ${shared}
  - tail
```

读取结果：

```python
{"items": ["head", "a", "b", "tail"]}
```

### Mapping 合并

`${base}` 独占一行并且同级存在普通键时，会把引用到的 mapping 合并进当前位置。同名字段双方都是 mapping 时继续合并，否则本地值覆盖引用值。

```yaml
base:
  db:
    host: 127.0.0.1
    port: 5432
  debug: false

app:
  ${base}
  db:
    port: 15432
```

读取结果：

```python
{
    "app": {
        "db": {
            "host": "127.0.0.1",
            "port": 15432,
        },
        "debug": False,
    }
}
```

## TOML

支持的后缀：

- `.toml`

## CSV

支持的后缀：

- `.csv`

CSV 只支持两种形态：

### 键值表

表头为 `key,value`，且文件只有这两列时，读取结果是 `dict`。表头大小写不影响判断。

```csv
key,value
host,127.0.0.1
port,5432
```

读取结果：

```python
{"host": "127.0.0.1", "port": "5432"}
```

### 记录表

其它合法多列表头会读取成 `list[dict]`。

```csv
name,host,port
main,127.0.0.1,5432
backup,127.0.0.2,5433
```

读取结果：

```python
[
    {"name": "main", "host": "127.0.0.1", "port": "5432"},
    {"name": "backup", "host": "127.0.0.2", "port": "5433"},
]
```