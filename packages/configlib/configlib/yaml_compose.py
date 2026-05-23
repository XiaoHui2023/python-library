from __future__ import annotations

import copy
import re
from typing import Any, Literal

SPREAD_KEY = "__configlib_spread__"
MERGES_KEY = "__configlib_merges__"

_BARE_VAR_LINE = re.compile(r"^(\s*)(\$\{[^{}]+\})\s*(#.*)?$")
_RESERVED_KEYS = frozenset({SPREAD_KEY, MERGES_KEY})


def preprocess_yaml_compose(source: str) -> str:
    """将块式 YAML 中独占一行的 ${} 改写成可解析的占位结构。"""
    if not source:
        return source
    lines = source.splitlines(keepends=True)
    if not lines:
        return source

    infos = [_line_info(line) for line in lines]
    out: list[str] = []
    i = 0
    while i < len(lines):
        info = infos[i]
        if not info.is_bare_var:
            out.append(lines[i])
            i += 1
            continue

        parent_indent = _parent_indent(infos, i)
        block_end = _block_end_index(infos, i, parent_indent)
        block = infos[i:block_end]
        siblings = _siblings_at_indent(infos, i, parent_indent)
        mode = _infer_block_mode(siblings)

        if mode == "seq":
            for entry in block:
                if entry.is_bare_var:
                    out.append(
                        f"{entry.indent_str}- {SPREAD_KEY}: {entry.bare_expr}{entry.comment_suffix}\n"
                    )
            i = block_end
            continue

        merge_exprs = [entry.bare_expr for entry in block if entry.is_bare_var]
        if merge_exprs:
            base_indent = block[0].indent_str
            out.append(f"{base_indent}{MERGES_KEY}:\n")
            for expr in merge_exprs:
                out.append(f"{base_indent}  - {expr}\n")
        i = block_end

    if source.endswith("\n") and out and not out[-1].endswith("\n"):
        out[-1] = out[-1] + "\n"
    return "".join(out)


def apply_composition(data: Any) -> Any:
    """在变量解析完成后展开列表拼接与字典合并占位。"""
    if isinstance(data, dict):
        return _compose_mapping(data)
    if isinstance(data, list):
        return _compose_sequence(data)
    return data


class _LineInfo:
    __slots__ = (
        "indent",
        "indent_str",
        "is_bare_var",
        "bare_expr",
        "comment_suffix",
        "is_dash_item",
        "is_mapping_entry",
        "is_blank",
    )

    def __init__(self, line: str) -> None:
        stripped = line.lstrip(" \t")
        self.indent = len(line) - len(stripped)
        self.indent_str = line[: self.indent]
        self.is_blank = not stripped or stripped.startswith("#")
        self.is_dash_item = stripped.startswith("- ")
        self.is_mapping_entry = (
            not self.is_blank
            and not self.is_dash_item
            and ":" in stripped
            and not stripped.startswith("${")
        )
        match = _BARE_VAR_LINE.match(stripped)
        self.is_bare_var = match is not None and not self.is_blank
        self.bare_expr = match.group(2) if match else ""
        self.comment_suffix = match.group(3) or "" if match else ""


def _line_info(line: str) -> _LineInfo:
    return _LineInfo(line)


def _parent_indent(infos: list[_LineInfo], index: int) -> int:
    indent = infos[index].indent
    for pos in range(index - 1, -1, -1):
        info = infos[pos]
        if info.is_blank:
            continue
        if info.indent < indent:
            return info.indent
    return -1


def _siblings_at_indent(
    infos: list[_LineInfo],
    index: int,
    parent_indent: int,
) -> list[_LineInfo]:
    indent = infos[index].indent
    siblings: list[_LineInfo] = []
    for pos, info in enumerate(infos):
        if info.is_blank:
            continue
        if info.indent != indent:
            continue
        if _parent_indent(infos, pos) != parent_indent:
            continue
        siblings.append(info)
    return siblings


def _block_end_index(infos: list[_LineInfo], start: int, parent_indent: int) -> int:
    indent = infos[start].indent
    pos = start
    while pos < len(infos):
        info = infos[pos]
        if not info.is_blank and info.indent < indent and pos > start:
            break
        if not info.is_blank and info.indent == indent:
            if pos > start and not info.is_bare_var:
                break
        if not info.is_blank and info.indent > indent:
            pos += 1
            continue
        pos += 1
    return pos


def _infer_block_mode(block: list[_LineInfo]) -> Literal["seq", "map"]:
    for info in block:
        if info.is_dash_item:
            return "seq"
        if info.is_mapping_entry:
            return "map"
    return "map"


def _deep_merge_dict(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """递归合并 mapping；双方均为 dict 的同名键继续下钻，否则由 overlay 覆盖。"""
    result = copy.deepcopy(base)
    for key, value in overlay.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge_dict(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _compose_mapping(data: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    merge_sources: list[dict[str, Any]] = []

    for key, value in data.items():
        if key == MERGES_KEY:
            resolved = _compose_sequence(value) if isinstance(value, list) else value
            if not isinstance(resolved, list):
                raise TypeError(f"{MERGES_KEY} 必须是列表")
            for item in resolved:
                if not isinstance(item, dict):
                    raise TypeError(f"{MERGES_KEY} 每一项必须是字典")
                merge_sources.append(apply_composition(item))
            continue
        if key in _RESERVED_KEYS:
            raise ValueError(f"保留键 {key!r} 只能由预处理生成")
        merged[key] = apply_composition(value)

    result: dict[str, Any] = {}
    for source in merge_sources:
        result = _deep_merge_dict(result, source)
    return _deep_merge_dict(result, merged)


def _compose_sequence(data: list[Any]) -> list[Any]:
    result: list[Any] = []
    for item in data:
        if isinstance(item, dict) and SPREAD_KEY in item and len(item) == 1:
            spread_value = apply_composition(item[SPREAD_KEY])
            if not isinstance(spread_value, list):
                raise TypeError(f"{SPREAD_KEY} 必须是列表")
            result.extend(spread_value)
            continue
        if isinstance(item, dict) and SPREAD_KEY in item:
            raise ValueError(f"{SPREAD_KEY} 不能与其他键混用")
        result.append(apply_composition(item))
    return result


__all__ = [
    "SPREAD_KEY",
    "MERGES_KEY",
    "preprocess_yaml_compose",
    "apply_composition",
]
