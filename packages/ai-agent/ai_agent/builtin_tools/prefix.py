from __future__ import annotations

APP_BUILTIN_PREFIX = "builtin"


def builtin_tool_name(short: str) -> str:
    """生成应用级内置工具对外名，形如 ``builtin__current_time``。"""
    key = short.strip()
    if not key:
        raise ValueError("内置工具短名不能为空")
    return f"{APP_BUILTIN_PREFIX}__{key}"
