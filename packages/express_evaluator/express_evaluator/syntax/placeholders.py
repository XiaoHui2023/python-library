from __future__ import annotations

from ..registry import register_syntax


@register_syntax(
    "placeholders",
)
class PlaceholderSyntax:
    """启用占位符解析，如 {user.profile.name}"""
    pass