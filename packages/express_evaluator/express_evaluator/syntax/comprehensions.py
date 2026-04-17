from __future__ import annotations

import ast

from ..registry import register_syntax


@register_syntax(
    "comprehensions",
    ast_nodes=(ast.ListComp, ast.GeneratorExp, ast.comprehension),
)
class ComprehensionSyntax:
    """启用列表推导和生成器表达式"""
    pass