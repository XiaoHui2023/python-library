import os
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from .resolver import resolve_variables

SUFFIXES = {'.toml'}


def is_toml(file_path: str) -> bool:
    return os.path.splitext(file_path)[1] in SUFFIXES


def load_toml(file_path: str) -> dict:
    with open(file_path, "rb") as f:
        data = tomllib.load(f)
    return resolve_variables(data)

def load_toml_raw(file_path: str) -> dict:
    with open(file_path, "rb") as f:
        return tomllib.load(f)

__all__ = ['is_toml', 'load_toml', 'load_toml_raw']