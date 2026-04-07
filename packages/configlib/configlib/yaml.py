from __future__ import annotations
import os
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any
import yaml
from .resolver import resolve_variables

SUFFIXES = {".yaml", ".yml"}
_YAML_LOAD_STACK: ContextVar[list[Path] | None] = ContextVar("_YAML_LOAD_STACK", default=None)


@contextmanager
def _include_guard(path: Path):
    """管理 include 循环检测栈，顶层调用结束后复位。"""
    stack = _YAML_LOAD_STACK.get()
    is_top_level = stack is None
    if is_top_level:
        stack = []
        _YAML_LOAD_STACK.set(stack)

    if path in stack:
        chain = " -> ".join(str(item) for item in [*stack, path])
        raise ValueError(f"检测到循环 include: {chain}")

    stack.append(path)
    try:
        yield
    finally:
        stack.pop()
        if is_top_level:
            _YAML_LOAD_STACK.set(None)


def is_yaml(file_path: str) -> bool:
    return os.path.splitext(file_path)[1] in SUFFIXES


def load_yaml(file_path: str) -> dict | list:
    path = Path(file_path).resolve()
    with _include_guard(path):
        data = _load_yaml_raw(path)
        return resolve_variables(data)


def load_yaml_raw(file_path: str) -> dict | list:
    """加载 YAML 但不解析变量（供 include 使用）"""
    path = Path(file_path).resolve()
    with _include_guard(path):
        return _load_yaml_raw(path)


def _load_yaml_raw(path: Path) -> Any:
    class _YamlIncludeLoader(yaml.SafeLoader):
        pass

    def construct_include(loader: _YamlIncludeLoader, node: yaml.Node) -> Any:
        relative_path = loader.construct_scalar(node)
        target_path = (path.parent / relative_path).resolve()
        from . import load_config_raw
        return load_config_raw(str(target_path))

    _YamlIncludeLoader.add_constructor("!include", construct_include)

    with path.open("r", encoding="utf-8") as f:
        return yaml.load(f, Loader=_YamlIncludeLoader)


__all__ = ["is_yaml", "load_yaml", "load_yaml_raw"]