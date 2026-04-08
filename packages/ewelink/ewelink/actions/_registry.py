from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._base import ActionBase

REGISTRY: dict[str, type[ActionBase]] = {}


def register(action: str):
    """装饰器：将 action 模型注册到 REGISTRY。"""
    def decorator(cls: type[ActionBase]) -> type[ActionBase]:
        if action in REGISTRY:
            raise ValueError(f"Duplicate action: {action!r}")
        cls.action_name = action
        REGISTRY[action] = cls
        return cls
    return decorator