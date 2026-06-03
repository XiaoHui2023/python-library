from __future__ import annotations

from typing import Any

from ai_agent.builtin_tools.prefix import builtin_tool_name
from ai_agent.harness.current_time import get_current_time
from ai_agent.tools import Tool

CURRENT_TIME_SHORT_NAME = "current_time"

_CURRENT_TIME_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "timezone": {
            "type": "string",
            "description": "IANA 时区名，如 Asia/Shanghai；省略则使用本机本地时区",
        },
    },
    "additionalProperties": False,
}


def harness_current_time_tool_name() -> str:
    """Harness 沙箱层同名工具的对外名，用于去重。"""
    return "harness__current_time"


def build_current_time_tool() -> Tool:
    """构造 ``builtin__current_time``，不依赖 Harness 工作区。"""
    return Tool(
        name=builtin_tool_name(CURRENT_TIME_SHORT_NAME),
        description="获取当前日期与时间（ISO 8601），可按 IANA 时区名指定时区。",
        parameters=_CURRENT_TIME_PARAMETERS,
        handler=_run_current_time,
    )


def _run_current_time(*, timezone: str = "") -> str:
    return get_current_time(timezone)
