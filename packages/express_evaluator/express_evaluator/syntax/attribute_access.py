from __future__ import annotations

import ast

from ..registry import register_syntax


@register_syntax(
    "attribute_access",
    ast_nodes=(ast.Attribute,),
)
class AttributeAccessSyntax:
    """启用属性访问，如 x.name"""
    pass