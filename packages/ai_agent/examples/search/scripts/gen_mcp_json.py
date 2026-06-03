from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, TypedDict


class _ToolServerSpec(TypedDict):
    name: str
    module: str
    rel_path: str


# 新增 tools 仓库 MCP 工具时在此追加一项，并同步 mcp.json.example
_TOOL_SERVERS: list[_ToolServerSpec] = [
    {
        "name": "bocha_search",
        "module": "mcp_tool_bocha_search",
        "rel_path": "../../../tools/bocha_search",
    },
]

_DEFAULT_BOCHA_ENV: dict[str, str] = {
    "BOCHA_API_KEY": "",
    "LLM_API_KEY": "",
    "LLM_BASE_URL": "",
    "LLM_MODEL": "",
    "BOCHA_FETCH_TIMEOUT": "3",
    "BOCHA_MAX_WORKERS": "10",
    "BOCHA_MAX_CHARS": "10000",
}


def _venv_python(tool_root: Path) -> Path:
    if sys.platform == "win32":
        return tool_root / ".venv" / "Scripts" / "python.exe"
    return tool_root / ".venv" / "bin" / "python"


def _server_entry(package_root: Path, spec: _ToolServerSpec) -> dict[str, object]:
    tool_root = (package_root / spec["rel_path"]).resolve()
    python = _venv_python(tool_root)
    if not python.is_file():
        print(
            f"未找到 {python}，请先在 {tool_root} 运行 update.bat",
            file=sys.stderr,
        )
        sys.exit(1)
    entry: dict[str, object] = {
        "command": str(python),
        "args": ["-m", spec["module"]],
        "cwd": str(tool_root),
    }
    if spec["name"] == "bocha_search":
        entry["env"] = dict(_DEFAULT_BOCHA_ENV)
    return entry


def _merge_servers(
    existing: dict[str, Any] | None,
    fresh_servers: dict[str, dict[str, object]],
) -> dict[str, object]:
    prior_servers = (existing or {}).get("mcpServers")
    if not isinstance(prior_servers, dict):
        prior_servers = {}

    merged_servers: dict[str, object] = {}
    for name, entry in fresh_servers.items():
        merged: dict[str, object] = dict(entry)
        old = prior_servers.get(name)
        if isinstance(old, dict) and isinstance(old.get("env"), dict):
            merged["env"] = {str(k): str(v) for k, v in old["env"].items()}
        merged_servers[name] = merged

    return {"mcpServers": merged_servers}


def main() -> None:
    example_root = Path(__file__).resolve().parent.parent
    package_root = example_root.parents[1]
    output = example_root / "mcp.json"

    fresh_servers = {
        spec["name"]: _server_entry(package_root, spec)
        for spec in _TOOL_SERVERS
    }

    existing: dict[str, Any] | None = None
    if output.is_file():
        existing = json.loads(output.read_text(encoding="utf-8"))

    config = _merge_servers(existing, fresh_servers)
    output.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"已写入 {output}")
    print("请在 mcp.json 各 server 的 env 中填写密钥；示例脚本的 LLM 配置写在同目录 .env（勿提交）")


if __name__ == "__main__":
    main()
