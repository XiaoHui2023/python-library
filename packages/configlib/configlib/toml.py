import os
import tomli

SUFFIXS = [
    '.toml',
]

def is_toml(file_path:str) -> bool:
    """判断文件是否为toml文件"""
    return os.path.splitext(file_path)[1] in SUFFIXS

def load_toml(file_path:str) -> dict|list:
    """加载toml文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        return tomli.loads(f.read())

__all__ = [
    'is_toml',
    'load_toml',
]