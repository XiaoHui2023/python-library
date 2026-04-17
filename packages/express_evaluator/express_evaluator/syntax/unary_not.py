from __future__ import annotations

import ast

from ..registry import register_syntax


@register_syntax(
    "unary_not",
    ast_nodes=(ast.UnaryOp, ast.Not),
)
class UnaryNotSyntax:
    """启用一元否定，如 not x"""
    pass