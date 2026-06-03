from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from ai_agent.context import ToolInvocation


@dataclass
class Tool:
    """可注册到 Agent 的工具；由库内执行并写回 ToolInvocation.answer。"""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Any]

    def to_api(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    async def run(self, arguments: dict[str, Any]) -> tuple[bool, str]:
        """
        执行工具处理函数。

        Returns:
            是否成功、写入 invocation.answer 的文本
        """
        try:
            result = self.handler(**arguments)
            if isinstance(result, Awaitable):
                result = await result
            return True, str(result)
        except Exception as exc:  # noqa: BLE001 — 工具边界统一收口
            return False, str(exc)


class ToolRegistry:
    """
    按来源分层维护工具，对外平铺为 OpenAI tools。

    层顺序：基础 → skill 管理 → 已启用 skill 子工具 → 额外注入；重名时报错。
    """

    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._base: dict[str, Tool] = {}
        self._management: dict[str, Tool] = {}
        self._skill: dict[str, Tool] = {}
        self._extra: dict[str, Tool] = {}
        self._flat: dict[str, Tool] = {}
        if tools:
            for tool in tools:
                self._base[tool.name] = tool
        self._rebuild_flat()

    def set_base_tools(self, tools: list[Tool]) -> None:
        """替换基础工具层（如 Harness 沙箱工具）。"""
        self._base = {tool.name: tool for tool in tools}
        self._rebuild_flat()

    def set_management_tools(self, tools: list[Tool]) -> None:
        """替换 skill 管理工具层。"""
        self._management = {tool.name: tool for tool in tools}
        self._rebuild_flat()

    def set_skill_tools(self, tools: list[Tool]) -> None:
        """替换当前已启用 skill 暴露的子工具层。"""
        self._skill = {tool.name: tool for tool in tools}
        self._rebuild_flat()

    def set_extra_tools(self, tools: list[Tool]) -> None:
        """替换额外注入工具（如 MCP）。"""
        self._extra = {tool.name: tool for tool in tools}
        self._rebuild_flat()

    def register(self, tool: Tool) -> None:
        """向额外层注册单个工具（与 ``set_extra_tools`` 同层，可覆盖同名）。"""
        self._extra[tool.name] = tool
        self._rebuild_flat()

    def effective_tools(self) -> list[Tool]:
        """当前合并后的全部工具实例。"""
        return list(self._flat.values())

    def api_tools(self) -> list[dict[str, Any]]:
        return [tool.to_api() for tool in self._flat.values()]

    def get(self, name: str) -> Tool | None:
        return self._flat.get(name)

    async def execute(self, invocation: ToolInvocation) -> None:
        """执行一次调用并更新 invocation 的 answer / ok。"""
        tool = self.get(invocation.tool_name)
        if tool is None:
            invocation.ok = False
            invocation.answer = f"unknown tool: {invocation.tool_name}"
            return
        ok, text = await tool.run(invocation.arguments)
        invocation.ok = ok
        invocation.answer = text

    def _rebuild_flat(self) -> None:
        merged: dict[str, Tool] = {}
        for layer_name, layer in (
            ("base", self._base),
            ("management", self._management),
            ("skill", self._skill),
            ("extra", self._extra),
        ):
            for name, tool in layer.items():
                if name in merged:
                    raise ValueError(
                        f"工具名冲突: {name!r}（{layer_name} 与已有层重复）"
                    )
                merged[name] = tool
        self._flat = merged
