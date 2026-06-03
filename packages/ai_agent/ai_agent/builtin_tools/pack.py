from __future__ import annotations

from ai_agent.builtin_tools.current_time import build_current_time_tool
from ai_agent.tools import Tool


def build_app_builtin_tools(*, current_time: bool) -> list[Tool]:
    """
    组装 AgentApp 可选的应用级内置工具（与 Harness 沙箱无关）。

    Args:
        current_time: 是否注册 ``builtin__current_time``

    Returns:
        待并入 ToolRegistry 基础层的工具列表
    """
    tools: list[Tool] = []
    if current_time:
        tools.append(build_current_time_tool())
    return tools
