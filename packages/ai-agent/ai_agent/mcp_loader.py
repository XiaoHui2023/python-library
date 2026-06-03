from __future__ import annotations

from collections.abc import Mapping
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import get_default_environment, stdio_client

from ai_agent.mcp_config import McpConfig, McpStdioServerConfig, parse_mcp_config
from ai_agent.tools import Tool


def _stdio_env(server_env: dict[str, str] | None) -> dict[str, str]:
    """
    组装 MCP 子进程环境变量。

    仅合并 MCP SDK 默认项与 ``mcp.json`` 中该 server 的 ``env``，
    不继承当前进程的 ``os.environ``，避免与示例 ``.env`` 中的 LLM 等变量串扰。
    """
    merged = dict(get_default_environment())
    if server_env:
        merged.update(server_env)
    return merged


class MCPToolLoader:
    """
    按已校验的 MCP 配置启动 stdio 服务并保持会话，将远程工具包装为库内 ``Tool``。

    会话在 ``close()`` 之前须保持存活，以便后续 ReAct 循环通过同一连接调用工具。
    配置文件读取与多格式解析由调用方负责，本类只接收 ``McpConfig`` 或等价映射。
    """

    def __init__(self) -> None:
        self._stack = AsyncExitStack()

    async def load(self, config: McpConfig | Mapping[str, Any]) -> list[Tool]:
        """
        按配置启动全部 MCP server 并收集工具。

        Args:
            config: ``McpConfig`` 或含 ``mcpServers`` 的映射（经 Pydantic 校验）

        Returns:
            各 server 暴露的工具列表
        """
        parsed = parse_mcp_config(config)
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
        params = StdioServerParameters(
            command=server_config.command,
            args=server_config.args,
            env=_stdio_env(server_config.env),
            cwd=server_config.cwd,
        )

        read, write = await self._stack.enter_async_context(stdio_client(params))
        session = await self._stack.enter_async_context(ClientSession(read, write))
        await session.initialize()

        result = await session.list_tools()
        tools: list[Tool] = []

        for mcp_tool in result.tools:
            ai_tool_name = f"{server_name}__{mcp_tool.name}"
            handler = _make_tool_handler(session, mcp_tool.name)
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
) -> Any:
    async def handler(**arguments: Any) -> str:
        call_result = await session.call_tool(mcp_tool_name, arguments)
        return MCPToolLoader._result_to_text(call_result)

    return handler
