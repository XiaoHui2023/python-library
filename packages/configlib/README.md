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

### 列表合并

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

### 字典合并

假如有以下变量

```yaml
var:
  a:
    name: "name is a"
    age: 99
```

将 `var` 的内容嵌入其他字典里，并重载 `a.age`。由于是`深合并`，只覆盖最底层的键。

```yaml
root:
  ${var}
  a:
    age: -1
```

`root` 的结果为：

```python
{
  "root": {
      "a": {
          "name": "name is a",
          "age": -1
      }
  }
}
```

### 导入

```yaml
a: !include 1.yaml 2.json 3.toml 4.csv # 多个按顺序导入

app:
  base: !include base.yaml # 作为base键对应的值导入
  !include other_dict.yml # 作为另一个dict合并到app，属于字典合并

items:
  - !include item.yaml # 作为一个元素
  !include other_list.json # 作为另一个list合并到items，属于列表合并
```

多文件导入用于`list`和`dict`合并，合并进去的文件内容也必须是`list`或`dict`。

## TOML

支持的后缀：

- `.toml`

## CSV

支持的后缀：

- `.csv`

首行为表头，表示键。其余每行表示对应的值：

```csv
name,host,port
main,127.0.0.1,5432
backup,127.0.0.2,5433
```

读取结果：

```python
[
    {"name": "main", "host": "127.0.0.1", "port": "5432"},
    {"name": "backup", "host": "127.0.0.2", "port": "5433"}
]
```
