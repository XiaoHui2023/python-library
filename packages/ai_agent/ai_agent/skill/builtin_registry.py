from __future__ import annotations

from collections.abc import Callable

from ai_agent.tools import Tool

ToolFactory = Callable[[], Tool]


class BuiltinToolRegistry:
    """
    宿主预注册的安全工具库，供技能 frontmatter 以内置引用方式绑定。

    不允许从技能文件动态执行任意 Python；未注册名称在启用技能时无法解析。
    """

    def __init__(self) -> None:
        self._factories: dict[str, ToolFactory] = {}

    def register(self, name: str, factory: ToolFactory) -> None:
        """
        注册内置工具工厂。

        Args:
            name: 不含 ``builtin:`` 前缀的名称
            factory: 每次绑定 skill 时调用，返回新的 Tool 实例
        """
        key = name.strip()
        if not key:
            raise ValueError("内置工具名不能为空")
        self._factories[key] = factory

    def resolve(self, handler: str) -> Tool | None:
        """
        解析 handler 引用。

        Args:
            handler: 形如 ``builtin:tool_name``

        Returns:
            可注册的 Tool；未知 handler 时返回 None
        """
        cleaned = handler.strip()
        if not cleaned.startswith("builtin:"):
            return None
        name = cleaned[len("builtin:") :].strip()
        if not name:
            return None
        factory = self._factories.get(name)
        if factory is None:
            return None
        return factory()

    def known_names(self) -> tuple[str, ...]:
        """已注册的内置工具名。"""
        return tuple(sorted(self._factories))
