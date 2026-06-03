from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_mcp_json_document(path: Path) -> dict[str, Any]:
    """
    读取示例用 ``mcp.json``（仅 ``mcpServers``）。

    Args:
        path: ``mcp.json`` 路径（须显式传入，仅 search 等 MCP 示例使用）

    Raises:
        ValueError: 文件不存在、JSON 无效或含非 MCP 顶层键
    """
    if not path.is_file():
        raise ValueError(
            f"缺少 {path}，请复制 examples/search/mcp.json.example 为 mcp.json 并填写",
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} 不是合法 JSON") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path} 根节点须为对象")
    _reject_non_mcp_top_level(data, path)
    return data


def _reject_non_mcp_top_level(document: dict[str, Any], path: Path) -> None:
    extra = set(document.keys()) - {"mcpServers"}
    if not extra:
        return
    if "agentEnv" in extra:
        raise ValueError(
            f"{path} 含 agentEnv；示例脚本的 LLM 配置请写入同目录 .env，"
            "mcp.json 仅保留 mcpServers",
        )
    raise ValueError(f"{path} 含未知顶层键：{sorted(extra)}")


def mcp_servers_payload(document: dict[str, Any]) -> dict[str, Any]:
    """
    取出 ``mcpServers`` 供 ``parse_mcp_config`` 使用。

    Raises:
        ValueError: 缺少 ``mcpServers``
    """
    servers = document.get("mcpServers")
    if not isinstance(servers, dict):
        raise ValueError("mcp.json 缺少 mcpServers 对象")
    return {"mcpServers": servers}
