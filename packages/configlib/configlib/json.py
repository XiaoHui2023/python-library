import json5
import os

from .resolver import resolve_variables

SUFFIXES = {'.json', '.json5'}


def is_json(file_path: str) -> bool:
    return os.path.splitext(file_path)[1] in SUFFIXES


def load_json(file_path: str) -> dict | list:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json5.load(f)
    return resolve_variables(data)

def load_json_raw(file_path: str) -> dict | list:
    with open(file_path, 'r', encoding='utf-8') as f:
        return json5.load(f)

__all__ = ['is_json', 'load_json', 'load_json_raw']