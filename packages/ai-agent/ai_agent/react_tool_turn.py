from __future__ import annotations

from ai_agent.builtin_tools.current_time import (
    CURRENT_TIME_SHORT_NAME,
    harness_current_time_tool_name,
)
from ai_agent.builtin_tools.prefix import builtin_tool_name
from ai_agent.context import ToolInvocation

_BUILTIN_CURRENT_TIME = builtin_tool_name(CURRENT_TIME_SHORT_NAME)
_HARNESS_CURRENT_TIME = harness_current_time_tool_name()

_SAME_TURN_DEFERRED_TOOL_REPLY = (
    "未执行：本回合已与取时工具同时发起。请先阅读同回合取时工具的返回，"
    "再在下一回合单独调用本工具并据取时结果重写参数（勿复用本回合已生成的 query）。"
)


def is_current_time_tool(tool_name: str) -> bool:
    """是否为应用或 Harness 的取时工具对外名。"""
    return tool_name in (_BUILTIN_CURRENT_TIME, _HARNESS_CURRENT_TIME)


def batch_includes_current_time(batch: list[ToolInvocation]) -> bool:
    return any(is_current_time_tool(inv.tool_name) for inv in batch)


def should_defer_tool_in_batch(inv: ToolInvocation, batch: list[ToolInvocation]) -> bool:
    """
    同回合若同时请求取时与其它工具，仅执行取时；其它工具返回说明性结果供下回合重试。
    """
    if is_current_time_tool(inv.tool_name):
        return False
    return batch_includes_current_time(batch)


def deferred_tool_reply() -> str:
    """推迟执行时写入 ``ToolInvocation.answer`` 的固定说明。"""
    return _SAME_TURN_DEFERRED_TOOL_REPLY
