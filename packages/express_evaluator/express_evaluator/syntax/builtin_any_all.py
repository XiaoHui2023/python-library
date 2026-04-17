from __future__ import annotations

import ast
from collections.abc import Iterable, Mapping
from typing import Any

from ..registry import register_syntax


def _read_member(value: Any, name: str) -> Any:
    if name.startswith("_"):
        raise ValueError(f"Private attribute access is not allowed: {name!r}")

    if isinstance(value, Mapping) and name in value:
        return value[name]

    if hasattr(value, name):
        return getattr(value, name)

    raise ValueError(f"Cannot read attribute/key {name!r} from {type(value).__name__!r}")


def builtin_any(values: Iterable[Any], attr: str | None = None) -> bool:
    if attr is None:
        return any(values)
    return any(_read_member(item, attr) for item in values)


def builtin_all(values: Iterable[Any], attr: str | None = None) -> bool:
    if attr is None:
        return all(values)
    return all(_read_member(item, attr) for item in values)


@register_syntax(
    "builtin_any_all",
    ast_nodes=(ast.Call,),
    functions={
        "any": builtin_any,
        "all": builtin_all,
    },
)
class BuiltinAnyAllSyntax:
    """启用 any() 和 all()，支持 any(items) 和 any(items, 'field')"""
    pass