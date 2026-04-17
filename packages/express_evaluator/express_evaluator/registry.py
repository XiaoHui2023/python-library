from __future__ import annotations

import ast
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from .errors import SyntaxRegistrationError


@dataclass(frozen=True, slots=True)
class SyntaxSpec:
    name: str
    ast_nodes: tuple[type[ast.AST], ...] = ()
    functions: Mapping[str, Callable[..., Any]] = field(default_factory=dict)


_SYNTAX_REGISTRY: dict[str, SyntaxSpec] = {}


def register_syntax(
    name: str,
    *,
    ast_nodes: tuple[type[ast.AST], ...] = (),
    functions: Mapping[str, Callable[..., Any]] | None = None,
):
    def decorator(obj: Any) -> Any:
        if name in _SYNTAX_REGISTRY:
            raise SyntaxRegistrationError(f"Syntax {name!r} already registered")

        _SYNTAX_REGISTRY[name] = SyntaxSpec(
            name=name,
            ast_nodes=tuple(ast_nodes),
            functions=dict(functions or {}),
        )
        return obj

    return decorator


def get_syntax(name: str) -> SyntaxSpec:
    """获取指定名称的语法"""
    if not has_syntax(name):
        raise SyntaxRegistrationError(f"Syntax {name!r} not registered")
    return _SYNTAX_REGISTRY[name]


def has_syntax(name: str) -> bool:
    """检查指定名称的语法是否注册"""
    return name in _SYNTAX_REGISTRY


def iter_syntaxes() -> tuple[SyntaxSpec, ...]:
    """获取所有语法列表"""
    return tuple(_SYNTAX_REGISTRY.values())


def syntax_names() -> tuple[str, ...]:
    """获取所有语法名称列表"""
    return tuple(_SYNTAX_REGISTRY.keys())

def get_syntaxs(names: list[str]) -> list[SyntaxSpec]:
    """获取指定名称的语法列表"""
    return [get_syntax(name) for name in names]