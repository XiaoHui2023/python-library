from __future__ import annotations

import ast

from ..registry import register_syntax


@register_syntax(
    "bool_ops",
    ast_nodes=(ast.BoolOp, ast.And, ast.Or),
)
class BoolOpSyntax:
    """启用布尔运算，如 and / or"""
    pass