from __future__ import annotations

import ast

from ..registry import register_syntax


@register_syntax(
    "literals",
    ast_nodes=(ast.Constant, ast.List, ast.Tuple),
)
class LiteralSyntax:
    """启用常量、列表和元组"""
    pass