from __future__ import annotations

import sys
import time
from collections.abc import Mapping
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ai_agent.mcp_config import McpConfig, McpStdioServerConfig, parse_mcp_config
from ai_agent.mcp_debug import McpDebugLog
from ai_agent.tools import Tool


def _stdio_env(server_env: dict[str, str] | None) -> dict[str, str]:
    """
    组装 MCP 子进程环境变量。

    仅合并 MCP SDK 默认项与 ``mcp.json`` 中该 server 的 ``env``，
    不继承当前进程的 ``os.environ``，避免与示例 ``.env`` 中的 LLM 等变量串扰。
    """
    from mcp.client.stdio import get_default_environment

    merged = dict(get_default_environment())
    if server_env:
        merged.update(server_env)
    return merged


class MCPToolLoader:
    """
    按已校验的 MCP 配置启动 stdio 服务并保持会话，将远程工具包装为库内 ``Tool``。

    会话在 ``close()`` 之前须保持存活，以便后续 ReAct 循环通过同一连接调用工具。
    配置文件读取与多格式解析由调用方负责，本类只接收 ``McpConfig`` 或等价映射。

    调试：构造 ``debug_log_path`` 或设置环境变量 ``AI_AGENT_MCP_DEBUG_LOG``，
    记录 MCP 生命周期；server stderr 同时写入终端与上述日志文件。
    """

    def __init__(self, *, debug_log_path: str | Path | None = None) -> None:
        self._stack = AsyncExitStack()
        self._debug = McpDebugLog(debug_log_path)

    async def load(self, config: McpConfig | Mapping[str, Any]) -> list[Tool]:
        """
        按配置启动全部 MCP server 并收集工具。

        Args:
            config: ``McpConfig`` 或含 ``mcpServers`` 的映射（经 Pydantic 校验）

        Returns:
            各 server 暴露的工具列表
        """
        parsed = parse_mcp_config(config)
        self._debug.log("load mcp config")
        tools: list[Tool] = []
        for server_name, server_config in parsed.mcp_servers.items():
            server_tools = await self._load_server(server_name, server_config)
            tools.extend(server_tools)
        return tools

    async def _load_server(
        self,
        server_name: str,
        server_config: McpStdioServerConfig,
    ) -> list[Tool]:
        self._debug.log(f"start server {server_name}")
        params = StdioServerParameters(
            command=server_config.command,
            args=server_config.args,
            env=_stdio_env(server_config.env),
            cwd=server_config.cwd,
        )

        errlog = (
            self._debug.server_stderr_sink()
            if self._debug.enabled
            else sys.stderr
        )
        read, write = await self._stack.enter_async_context(
            stdio_client(params, errlog=errlog)
        )
        session = await self._stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        self._debug.log(f"initialize {server_name} ok")

        result = await session.list_tools()
        tool_names = ", ".join(t.name for t in result.tools) or "(none)"
        self._debug.log(f"list_tools {server_name} ok: {tool_names}")
        tools: list[Tool] = []

        for mcp_tool in result.tools:
            ai_tool_name = f"{server_name}__{mcp_tool.name}"
            handler = _make_tool_handler(
                session,
                mcp_tool.name,
                server_name=server_name,
                debug=self._debug,
            )
            tools.append(
                Tool(
                    name=ai_tool_name,
                    description=mcp_tool.description or "",
                    parameters=mcp_tool.inputSchema,
                    handler=handler,
                )
            )

        return tools

    async def close(self) -> None:
        """关闭已启动的 MCP 会话与 stdio 子进程。"""
        await self._stack.aclose()

    @staticmethod
    def _result_to_text(result: Any) -> str:
        parts: list[str] = []
        for item in getattr(result, "content", []):
            text = getattr(item, "text", None)
            if text is not None:
                parts.append(text)
        return "\n".join(parts)


def _make_tool_handler(
    session: ClientSession,
    mcp_tool_name: str,
    *,
    server_name: str,
    debug: McpDebugLog,
) -> Any:
    async def handler(**arguments: Any) -> str:
        label = f"{server_name}.{mcp_tool_name}"
        debug.log(f"call_tool {label} start")
        started = time.monotonic()
        try:
            call_result = await session.call_tool(mcp_tool_name, arguments)
        except Exception as exc:
            elapsed = time.monotonic() - started
            debug.log(
                f"call_tool {label} error after {elapsed:.1f}s: {exc!s}"
            )
            raise
        text = MCPToolLoader._result_to_text(call_result)
        elapsed = time.monotonic() - started
        debug.log(
            f"call_tool {label} returned, {len(text)} chars, {elapsed:.1f}s"
        )
        return text

    return handler
