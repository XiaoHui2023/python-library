from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ai_agent import MCPToolLoader, parse_mcp_config

from examples._support.load_example_mcp import load_example_mcp_json


def ensure_example_mcp_debug_logs(scratch_dir: Path) -> None:
    """
    为示例运行准备 MCP 调试日志路径（scratch 目录下两个文件）。

    仅当 ``AI_AGENT_MCP_DEBUG_LOG`` 尚未设置时写入默认值。
    """
    scratch_dir.mkdir(parents=True, exist_ok=True)
    if not os.environ.get("AI_AGENT_MCP_DEBUG_LOG", "").strip():
        os.environ["AI_AGENT_MCP_DEBUG_LOG"] = str(
            scratch_dir / "ai_agent.mcp.debug.log"
        )


def _inject_cursor_cli_debug_env(
    document: dict[str, Any],
    scratch_dir: Path,
) -> dict[str, Any]:
    servers = document.get("mcpServers")
    if not isinstance(servers, dict):
        return document
    cursor = servers.get("cursor_cli")
    if not isinstance(cursor, dict):
        return document
    env = dict(cursor.get("env") or {})
    if str(env.get("CURSOR_CLI_DEBUG_LOG", "")).strip():
        return document
    env["CURSOR_CLI_DEBUG_LOG"] = str(scratch_dir / "cursor_cli.mcp.stderr.log")
    return {
        **document,
        "mcpServers": {
            **servers,
            "cursor_cli": {**cursor, "env": env},
        },
    }


async def prepare_and_load_mcp_with_debug(
    example_dir: Path,
    scratch_dir: Path,
) -> tuple[list, MCPToolLoader]:
    """加载示例 MCP 工具，并启用 scratch 下默认调试日志路径。"""
    ensure_example_mcp_debug_logs(scratch_dir)
    document = load_example_mcp_json(example_dir)
    document = _inject_cursor_cli_debug_env(document, scratch_dir)
    loader = MCPToolLoader()
    tools = await loader.load(parse_mcp_config(document))
    return tools, loader
