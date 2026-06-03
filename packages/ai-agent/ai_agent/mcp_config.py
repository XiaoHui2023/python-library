from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class McpStdioServerConfig(BaseModel):
    """单个 MCP stdio 子进程启动项。"""

    model_config = ConfigDict(extra="forbid")

    command: str = Field(description="启动 MCP server 的可执行文件路径或命令名")
    args: list[str] = Field(default_factory=list, description="传给 command 的参数列表")
    env: dict[str, str] | None = Field(
        default=None,
        description="传入子进程的环境变量；与 MCP SDK 默认项合并，不继承宿主进程 os.environ",
    )
    cwd: str | None = Field(default=None, description="子进程工作目录；省略则使用当前工作目录")

    @field_validator("command")
    @classmethod
    def _command_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("command 不能为空")
        return stripped


class McpConfig(BaseModel):
    """MCP 工具加载配置，与常见 ``mcpServers`` JSON 结构一致。"""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    mcp_servers: dict[str, McpStdioServerConfig] = Field(
        alias="mcpServers",
        description="按名称索引的 MCP server 启动配置",
    )


def parse_mcp_config(data: McpConfig | Mapping[str, Any]) -> McpConfig:
    """
    将映射或已有模型规范为 ``McpConfig``。

    Args:
        data: 含 ``mcpServers`` 键的映射，或已校验的 ``McpConfig``

    Returns:
        校验后的配置模型
    """
    if isinstance(data, McpConfig):
        return data
    return McpConfig.model_validate(dict(data))
