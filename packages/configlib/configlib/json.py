import json5
import os

SUFFIXS = [
    '.json',
    '.json5',
]

def is_json(file_path:str) -> bool:
    """判断文件是否为json文件"""
    return os.path.splitext(file_path)[1] in SUFFIXS

def load_json(file_path:str) -> dict|list:
    """加载json文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json5.load(f)

__all__ = [
    'is_json',
    'load_json',
]