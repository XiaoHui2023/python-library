from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_agent import MCPToolLoader, parse_mcp_config


def load_example_mcp_json(example_dir: Path) -> dict[str, Any]:
    """
    读取示例目录 ``mcp.json``（仅 ``mcpServers``）。

    Args:
        example_dir: 示例根目录

    Raises:
        ValueError: 文件不存在、JSON 无效或含非 MCP 顶层键
    """
    path = example_dir / "mcp.json"
    if not path.is_file():
        raise ValueError(
            f"缺少 {path}；请复制 mcp.json.example 为 mcp.json，"
            "或合并各 tools/<name>/mcp.json 中的 mcpServers 段",
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} 不是合法 JSON") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path} 根节点须为对象")
    if "agentEnv" in data:
        raise ValueError(
            f"{path} 含 agentEnv；LLM 配置请写入同目录 .env，mcp.json 仅保留 mcpServers",
        )
    extra = set(data.keys()) - {"mcpServers"}
    if extra:
        raise ValueError(f"{path} 含未知顶层键：{sorted(extra)}")
    return data


async def prepare_and_load_mcp(example_dir: Path) -> tuple[list, MCPToolLoader]:
    """
    从示例目录 ``mcp.json`` 加载 MCP 工具。

    Args:
        example_dir: 示例根目录
    """
    document = load_example_mcp_json(example_dir)
    loader = MCPToolLoader()
    tools = await loader.load(parse_mcp_config(document))
    return tools, loader
