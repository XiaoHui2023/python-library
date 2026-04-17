from __future__ import annotations

import ast

from ..registry import register_syntax


@register_syntax(
    "comparisons",
    ast_nodes=(
        ast.Compare,
        ast.Eq,
        ast.NotEq,
        ast.Lt,
        ast.LtE,
        ast.Gt,
        ast.GtE,
        ast.Is,
        ast.IsNot,
        ast.In,
        ast.NotIn,
    ),
)
class ComparisonSyntax:
    """启用比较表达式，如 x == y"""
    pass