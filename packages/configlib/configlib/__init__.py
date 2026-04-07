from pathlib import Path

from .loader import ConfigLoader
from .json import is_json, load_json, load_json_raw
from .toml import is_toml, load_toml, load_toml_raw
from .yaml import is_yaml, load_yaml, load_yaml_raw


def load_config_raw(file_path: str | Path) -> dict | list:
    """加载配置文件（不解析变量）"""
    file_path = str(file_path)
    if is_json(file_path):
        return load_json_raw(file_path)
    elif is_toml(file_path):
        return load_toml_raw(file_path)
    elif is_yaml(file_path):
        return load_yaml_raw(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {file_path}")


def load_config(file_path: str | Path) -> dict | list:
    """加载配置文件"""
    file_path = str(file_path)
    if is_json(file_path):
        return load_json(file_path)
    elif is_toml(file_path):
        return load_toml(file_path)
    elif is_yaml(file_path):
        return load_yaml(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {file_path}")

__all__ = [
    "load_config",
    "load_config_raw",
    "ConfigLoader",
]