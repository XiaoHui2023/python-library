from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from ai_agent import (
    AgentApp,
    MCPToolLoader,
    RunInputPacket,
    parse_mcp_config,
)

from examples._support.demo_sandbox import clear_demo_sessions, session_ids_in_script
from examples._support.llm_config import load_llm_config
from examples._support.mcp_json_config import (
    load_mcp_json_document,
    mcp_servers_payload,
)
from examples._support.print_listener import create_print_listener
from examples._support.print_timing import ExamplePrintTiming

_EXAMPLE_DIR = Path(__file__).resolve().parent
_MCP_CONFIG_PATH = _EXAMPLE_DIR / "mcp.json"
_SANDBOX = _EXAMPLE_DIR / ".sandbox"
_BOCHA_SERVER = "bocha_search"
_SKILL_MARKER = "chat-search-answer"
_RULE_PATH = _EXAMPLE_DIR / "rules" / "assistant.md"

_ScriptStep = tuple[str, str, str, bool]

# 搜索与终稿：Bocha 查询 → 按 chat-search-answer 技能改写为聊天短答
_SCRIPT_STEPS: tuple[_ScriptStep, ...] = (
    (
        "demo",
        "用户",
        "用 Bocha 搜索今天的 AI 新闻，挑两条用聊天口吻告诉我。",
        False,
    ),
    (
        "demo",
        "用户",
        "再搜一下 OpenAI 最近一周有什么官方动态，简短总结一下。",
        False,
    ),
)


def _resolve_skills_root() -> Path:
    for ancestor in (_EXAMPLE_DIR, *_EXAMPLE_DIR.parents):
        root = ancestor / "skills"
        if (root / _SKILL_MARKER).is_dir():
            return root
    raise ValueError(
        f"未找到 skills/{_SKILL_MARKER}（已从 {_EXAMPLE_DIR} 向上查找）",
    )


async def _load_bocha_tools() -> tuple[list, MCPToolLoader | None]:
    document = load_mcp_json_document(_MCP_CONFIG_PATH)
    servers = mcp_servers_payload(document)
    if _BOCHA_SERVER not in servers["mcpServers"]:
        raise ValueError(
            f"mcp.json 须配置 {_BOCHA_SERVER!r}；可运行 examples/search/scripts/gen_mcp_json.py",
        )
    loader = MCPToolLoader()
    mcp_config = parse_mcp_config(
        {"mcpServers": {_BOCHA_SERVER: servers["mcpServers"][_BOCHA_SERVER]}},
    )
    tools = await loader.load(mcp_config)
    return tools, loader


def _build_app(cfg, tools: list, skills_root: Path) -> tuple[AgentApp, ExamplePrintTiming]:
    _SANDBOX.mkdir(parents=True, exist_ok=True)
    timing = ExamplePrintTiming()
    listener, _ = create_print_listener(
        model=cfg.model,
        base_url=cfg.base_url,
        timing=timing,
    )
    app = AgentApp(
        _SANDBOX,
        skill_roots={"skills": skills_root},
        rule_paths=[_RULE_PATH],
        api_key=cfg.api_key,
        model=cfg.model,
        base_url=cfg.base_url,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        thinking_enabled=cfg.thinking_enabled,
        memory_api_key=cfg.api_key,
        memory_model=cfg.model,
        memory_base_url=cfg.base_url,
        harness_enabled=False,
        listeners=listener,
    )
    app.set_shared_extra_tools(tools)
    return app, timing


async def _one_turn(
    app: AgentApp,
    timing: ExamplePrintTiming,
    *,
    session_id: str,
    user_name: str,
    request: str,
    clear: bool = False,
) -> str:
    timing.reset()
    output = await app.run(
        RunInputPacket(
            user_name=user_name,
            session_id=session_id,
            request=request,
            clear=clear,
        ),
    )
    return output.answer.strip()


async def _run_script(app: AgentApp, timing: ExamplePrintTiming) -> int:
    demo_sessions = session_ids_in_script(_SCRIPT_STEPS)
    clear_demo_sessions(_SANDBOX, demo_sessions)
    print(
        f"{timing.tag()} 演示前已清空会话: {', '.join(demo_sessions)}",
    )
    print()
    ok = True
    for session_id, user_name, request, clear in _SCRIPT_STEPS:
        timing.reset()
        print(f"{timing.tag()} --- 会话 {session_id} | 用户 {user_name} ---")
        print(f"{timing.tag()} > {request}")
        answer = await _one_turn(
            app,
            timing,
            session_id=session_id,
            user_name=user_name,
            request=request,
            clear=clear,
        )
        print(f"{timing.tag()} 回合结束")
        print()
        if not answer:
            ok = False
    return 0 if ok else 1


async def _run() -> int:
    loader: MCPToolLoader | None = None
    try:
        tools, loader = await _load_bocha_tools()
        print(f"已加载 {len(tools)} 个 MCP 工具（{_BOCHA_SERVER}）")
        skills_root = _resolve_skills_root()
        print(f"技能根：{skills_root}")

        cfg = load_llm_config(_EXAMPLE_DIR)
        app, timing = _build_app(cfg, tools, skills_root)
        return await _run_script(app, timing)
    finally:
        if loader is not None:
            await loader.close()


def main() -> None:
    try:
        code = asyncio.run(_run())
    except ValueError as exc:
        print(exc, file=sys.stderr)
        sys.exit(2)
    except Exception as exc:  # noqa: BLE001 — 示例入口统一打印
        print(exc, file=sys.stderr)
        sys.exit(1)
    sys.exit(code)


if __name__ == "__main__":
    main()
