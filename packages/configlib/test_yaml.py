from pathlib import Path
from configlib import load_config

def test_yaml() -> None:
    base_dir = Path(__file__).resolve().parent
    result = load_config(str(base_dir / "assets/example.yaml"))

    expected = {
        "app": {
            "name": "demo",
            "version": "1.0",
        },
        "base": {
            "title": "hello",
            "nested": {
                "value": 123,
            },
        },
        "json_data": {
            "user": {
                "name": "alice",
                "age": 18,
            },
        },
        "toml_data": {
            "server": {
                "host": "127.0.0.1",
                "port": 8080,
            },
        },
        "refs": {
            "app_name": "demo",
            "base_title": "hello",
            "local": {
                "name": "child",
                "parent_name": "child",
            },
        },
    }

    assert result == expected, f"结果不符合预期:\n实际={result}\n预期={expected}"
    print("测试yaml通过")