from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

SUFFIXS = [
    ".yaml",
    ".yml",
]

_VAR_PATTERN = re.compile(r"\$\{([^{}]+)\}")
_FULL_VAR_PATTERN = re.compile(r"^\$\{([^{}]+)\}$")
_YAML_LOAD_STACK: list[Path] = []


def is_yaml(file_path: str) -> bool:
    """判断文件是否为 yaml 文件"""
    return os.path.splitext(file_path)[1] in SUFFIXS


def load_yaml(file_path: str) -> dict | list:
    """加载 yaml 文件，支持 !include 和 ${} 变量解析"""
    path = Path(file_path).resolve()
    if path in _YAML_LOAD_STACK:
        chain = " -> ".join(str(item) for item in [*_YAML_LOAD_STACK, path])
        raise ValueError(f"检测到循环 include: {chain}")

    _YAML_LOAD_STACK.append(path)
    try:
        data = _load_yaml_raw(path)
        resolved = _VariableResolver(data).resolve()
    finally:
        _YAML_LOAD_STACK.pop()

    if not isinstance(resolved, (dict, list)):
        raise TypeError(f"yaml 顶层必须是 dict 或 list: {path}")
    return resolved


def _load_yaml_raw(path: Path) -> Any:
    class ConfigLoader(yaml.SafeLoader):
        """当前配置文件专用 Loader，用于按当前文件目录解析 include。"""

    def construct_include(loader: ConfigLoader, node: yaml.Node) -> Any:
        relative_path = loader.construct_scalar(node)
        target_path = (path.parent / relative_path).resolve()

        from . import load_config

        return load_config(str(target_path))

    ConfigLoader.add_constructor("!include", construct_include)

    with path.open("r", encoding="utf-8") as f:
        return yaml.load(f, Loader=ConfigLoader)


class _VariableResolver:
    """解析 ${a.b} 和 ${..c} 变量。"""

    def __init__(self, root: Any):
        self.root = root
        self._cache: dict[tuple[Any, ...], Any] = {}
        self._resolving: set[tuple[Any, ...]] = set()

    def resolve(self) -> Any:
        return self._resolve_at(())

    def _resolve_at(self, path: tuple[Any, ...]) -> Any:
        if path in self._cache:
            return self._cache[path]
        if path in self._resolving:
            raise ValueError(f"检测到循环变量引用: {self._format_path(path)}")

        self._resolving.add(path)
        try:
            node = self._get_node(path)
            resolved = self._resolve_node(node, path)
            self._cache[path] = resolved
            return resolved
        finally:
            self._resolving.remove(path)

    def _resolve_node(self, node: Any, path: tuple[Any, ...]) -> Any:
        if isinstance(node, dict):
            return {key: self._resolve_at(path + (key,)) for key in node}
        if isinstance(node, list):
            return [self._resolve_at(path + (index,)) for index, _ in enumerate(node)]
        if isinstance(node, str):
            return self._resolve_string(node, path)
        return node

    def _resolve_string(self, value: str, path: tuple[Any, ...]) -> Any:
        full_match = _FULL_VAR_PATTERN.fullmatch(value)
        if full_match:
            target_path = self._resolve_reference(full_match.group(1), path)
            return self._resolve_at(target_path)

        def replace(match: re.Match[str]) -> str:
            target_path = self._resolve_reference(match.group(1), path)
            return str(self._resolve_at(target_path))

        return _VAR_PATTERN.sub(replace, value)

    def _resolve_reference(self, expr: str, current_path: tuple[Any, ...]) -> tuple[Any, ...]:
        expr = expr.strip()
        if not expr:
            raise ValueError("变量表达式不能为空")

        if expr.startswith("."):
            return self._resolve_relative_path(expr, current_path)
        return self._split_path(expr)

    def _resolve_relative_path(
        self,
        expr: str,
        current_path: tuple[Any, ...],
    ) -> tuple[Any, ...]:
        dot_count = 0
        while dot_count < len(expr) and expr[dot_count] == ".":
            dot_count += 1

        if dot_count < 2 or dot_count % 2 != 0:
            raise ValueError(f"不支持的相对路径变量: {expr}")

        remainder = expr[dot_count:]
        if remainder.startswith(".") or not remainder:
            raise ValueError(f"不支持的相对路径变量: {expr}")

        up_levels = dot_count // 2
        mapping_paths = self._get_mapping_paths(current_path)
        if len(mapping_paths) < up_levels:
            raise ValueError(f"相对路径越界: {expr}，当前位置 {self._format_path(current_path)}")
        base_path = mapping_paths[-up_levels]
        return base_path + self._split_path(remainder)

    def _get_mapping_paths(self, current_path: tuple[Any, ...]) -> list[tuple[Any, ...]]:
        mapping_paths: list[tuple[Any, ...]] = []
        node = self.root
        walked: list[Any] = []

        if isinstance(node, dict):
            mapping_paths.append(())

        for key in current_path[:-1]:
            if isinstance(node, dict):
                node = node[key]
            elif isinstance(node, list):
                node = node[key]
            else:
                break

            walked.append(key)
            if isinstance(node, dict):
                mapping_paths.append(tuple(walked))

        return mapping_paths

    def _split_path(self, expr: str) -> tuple[Any, ...]:
        parts = [part.strip() for part in expr.split(".")]
        if any(not part for part in parts):
            raise ValueError(f"无效的变量路径: {expr}")

        result: list[Any] = []
        for part in parts:
            if part.isdigit():
                result.append(int(part))
            else:
                result.append(part)
        return tuple(result)

    def _get_node(self, path: tuple[Any, ...]) -> Any:
        node = self.root
        for key in path:
            try:
                node = node[key]
            except (KeyError, IndexError, TypeError) as exc:
                raise KeyError(f"变量引用不存在: {self._format_path(path)}") from exc
        return node

    def _format_path(self, path: tuple[Any, ...]) -> str:
        if not path:
            return "<root>"
        return ".".join(str(part) for part in path)


__all__ = [
    "is_yaml",
    "load_yaml",
]