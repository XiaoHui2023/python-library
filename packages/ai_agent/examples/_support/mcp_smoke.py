from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from ai_agent.tools import Tool

from examples._support.load_example_mcp import prepare_and_load_mcp
from examples._support.mcp_debug_paths import prepare_and_load_mcp_with_debug

_EXPECTED_TOOLS = frozenset(
    {
        "current_time__get_current_time",
        "cursor_cli__run_cursor_agent",
    },
)

_CURSOR_PROBE_FAILURE_MARKERS = (
    "Error executing tool",
    "退出码",
    "执行超过",
    "Cursor CLI 未安装",
)


def _find_tool(tools: list[Tool], name: str) -> Tool:
    for tool in tools:
        if tool.name == name:
            return tool
    raise ValueError(f"缺少 MCP 工具 {name}")


async def _with_mcp_tools(
    example_dir: Path,
    body: Callable[[list[Tool]], Awaitable[int]],
    *,
    scratch_dir: Path | None = None,
) -> int:
    if scratch_dir is not None:
        tools, loader = await prepare_and_load_mcp_with_debug(
            example_dir,
            scratch_dir,
        )
    else:
        tools, loader = await prepare_and_load_mcp(example_dir)
    try:
        return await body(tools)
    finally:
        await loader.close()


_FORBIDDEN_TOOLS = frozenset(
    {
        "cursor_cli__check_cursor_cli",
        "cursor_cli__install_cursor_cli",
    },
)


async def _verify_tool_list(tools: list[Tool]) -> int:
    names = sorted(tool.name for tool in tools)
    print(f"MCP 工具 ({len(names)}): {', '.join(names)}")
    missing = _EXPECTED_TOOLS - set(names)
    if missing:
        print(f"缺少预期工具: {', '.join(sorted(missing))}")
        return 1
    stale = _FORBIDDEN_TOOLS & set(names)
    if stale:
        print(
            "检测到已废止的 cursor_cli MCP 工具: "
            f"{', '.join(sorted(stale))}。"
            "请 bump tools/cursor_cli 版本号后重跑，或执行 "
            "`uv cache clean mcp-tool-cursor-cli`。",
        )
        return 1
    return 0


async def run_mcp_check(example_dir: Path, *, scratch_dir: Path | None = None) -> int:
    """
    从示例 ``mcp.json`` 加载 MCP，列出工具并调用取时。

    Args:
        example_dir: 含 ``mcp.json`` 的示例根目录
    """

    async def body(tools: list[Tool]) -> int:
        code = await _verify_tool_list(tools)
        if code != 0:
            return code
        time_tool = _find_tool(tools, "current_time__get_current_time")
        iso = (await time_tool.handler()).strip()
        print(f"current_time: {iso}")
        return 0

    return await _with_mcp_tools(example_dir, body, scratch_dir=scratch_dir)


async def run_mcp_probe(example_dir: Path, scratch_dir: Path) -> int:
    """
    在 ``run_mcp_check`` 基础上调用一次 ``cursor_cli__run_cursor_agent``。

    Args:
        example_dir: 含 ``mcp.json`` 的示例根目录
        scratch_dir: 传给 Cursor CLI 的 ``workspace``
    """

    async def body(tools: list[Tool]) -> int:
        code = await _verify_tool_list(tools)
        if code != 0:
            return code

        scratch_dir.mkdir(parents=True, exist_ok=True)
        time_tool = _find_tool(tools, "current_time__get_current_time")
        iso = (await time_tool.handler()).strip()
        today = iso[:10] if len(iso) >= 10 else iso
        print(f"current_time: {iso}")

        cursor_tool = _find_tool(tools, "cursor_cli__run_cursor_agent")
        task = f"今天是 {today}，今天是星期几？只答星期，不要解释。"
        print(f"probe task: {task}")
        print(f"workspace: {scratch_dir.resolve()}")
        result = (await cursor_tool.handler(
            task=task,
            workspace=str(scratch_dir.resolve()),
            allow_file_changes=False,
        )).strip()
        preview = result if len(result) <= 800 else f"{result[:800]}…"
        if not result:
            print("cursor_cli 返回为空")
            return 1
        if any(marker in result for marker in _CURSOR_PROBE_FAILURE_MARKERS):
            print(f"cursor_cli 探测失败:\n{preview}")
            return 1
        print(f"cursor_cli 返回:\n{preview}")
        return 0

    return await _with_mcp_tools(example_dir, body, scratch_dir=scratch_dir)
