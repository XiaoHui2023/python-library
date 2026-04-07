from __future__ import annotations

import os
import re
from typing import Any

_VAR_PATTERN = re.compile(r"\$\{([^{}]+)\}")

_SENTINEL = object()


def resolve_variables(data: Any) -> Any:
    """对已加载的配置数据进行 ${} 变量解析。"""
    return _VariableResolver(data).resolve()


def _auto_convert(value: str) -> str | int | float | bool | None:
    """将字符串自动转换为合适的 Python 类型。"""
    lower = value.strip().lower()
    if lower in ("true", "yes", "on"):
        return True
    if lower in ("false", "no", "off"):
        return False
    if lower in ("null", "none", "~"):
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


class _VariableResolver:
    """
    解析三种变量语法：
      - ${key.path}     绝对路径引用
      - ${..key}        相对路径引用
      - ${env:NAME}     显式环境变量
      - ${env:NAME:默认值}  带默认值的环境变量
    以及隐式回退：单级 ${KEY} 在配置中找不到时，自动查找同名环境变量。
    """

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
        full_match = _VAR_PATTERN.fullmatch(value)
        if full_match:
            expr = full_match.group(1)
            env_result = self._try_resolve_env(expr)
            if env_result is not _SENTINEL:
                return env_result
            target_path = self._resolve_reference(expr, path)
            return self._resolve_at(target_path)

        def replace(match: re.Match[str]) -> str:
            expr = match.group(1)
            env_result = self._try_resolve_env(expr)
            if env_result is not _SENTINEL:
                return str(env_result)
            target_path = self._resolve_reference(expr, path)
            return str(self._resolve_at(target_path))

        return _VAR_PATTERN.sub(replace, value)

    def _try_resolve_env(self, expr: str) -> Any:
        """解析 env:VAR 或 env:VAR:default。不匹配 env: 前缀则返回 _SENTINEL。"""
        expr = expr.strip()
        if not expr.startswith("env:"):
            return _SENTINEL

        rest = expr[4:]
        colon_pos = rest.find(":")
        if colon_pos == -1:
            env_name = rest.strip()
            default = _SENTINEL
        else:
            env_name = rest[:colon_pos].strip()
            default = rest[colon_pos + 1:]

        if not env_name:
            raise ValueError("环境变量名不能为空: ${env:}")

        value = os.environ.get(env_name)
        if value is not None:
            return _auto_convert(value)
        if default is not _SENTINEL:
            return _auto_convert(default)
        raise KeyError(f"环境变量不存在: {env_name}")

    # ---- 配置内引用 ----

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
            except (KeyError, IndexError, TypeError):
                if isinstance(key, int) and isinstance(node, dict):
                    try:
                        node = node[str(key)]
                        continue
                    except KeyError:
                        pass
                if len(path) == 1 and isinstance(path[0], str):
                    env_val = os.environ.get(path[0])
                    if env_val is not None:
                        return _auto_convert(env_val)
                raise KeyError(f"变量引用不存在: {self._format_path(path)}")
        return node

    def _format_path(self, path: tuple[Any, ...]) -> str:
        if not path:
            return "<root>"
        return ".".join(str(part) for part in path)


__all__ = [
    "resolve_variables",
]