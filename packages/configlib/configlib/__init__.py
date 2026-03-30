from .json import is_json,load_json
from .toml import is_toml,load_toml
from .yaml import is_yaml,load_yaml

def load_config(file_path:str) -> dict|list:
    """加载配置文件"""
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
]