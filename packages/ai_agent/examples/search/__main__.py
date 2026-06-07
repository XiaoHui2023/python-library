from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from ai_agent import AgentApp, RunInputPacket

from examples._support.demo_sandbox import clear_demo_sessions, session_ids_in_script
from examples._support.example_step import example_step
from examples._support.llm_config import load_llm_config
from examples._support.mcp_debug_paths import (
    ensure_example_mcp_debug_logs,
    prepare_and_load_mcp_with_debug,
)
from examples._support.mcp_smoke import run_mcp_check, run_mcp_probe
from examples._support.print_listener import create_print_listener
from examples._support.print_timing import ExamplePrintTiming

_EXAMPLE_DIR = Path(__file__).resolve().parent
_SANDBOX = _EXAMPLE_DIR / ".sandbox"
_SEARCH_SCRATCH = _EXAMPLE_DIR / "scratch"
_SKILL_MARKER = "chat-search-answer"
_RULE_PATH = _EXAMPLE_DIR / "rules" / "assistant.md"

_ScriptStep = tuple[str, str, str, bool]

_SCRIPT_STEPS: tuple[_ScriptStep, ...] = (
    (
        "demo",
        "用户",
        "搜索今天的 AI 新闻，挑两条用聊天口吻告诉我。",
        False,
    ),
    (
        "demo",
        "用户",
        "再搜一下 OpenAI 最近一周有什么官方动态，简短总结一下。",
        False,
    ),
)


def _write_workspace_rule() -> Path:
    path = _EXAMPLE_DIR / "rules" / "workspace.md"
    scratch = _SEARCH_SCRATCH.resolve()
    path.write_text(
        "## 本示例搜索工作区\n\n"
        f"调用 **cursor_cli__run_cursor_agent** 时 **workspace** 填：`{scratch}`\n",
        encoding="utf-8",
    )
    return path


def _resolve_skills_root() -> Path:
    for ancestor in (_EXAMPLE_DIR, *_EXAMPLE_DIR.parents):
        root = ancestor / "skills"
        if (root / _SKILL_MARKER).is_dir():
            return root
    raise ValueError(
        f"未找到 skills/{_SKILL_MARKER}（已从 {_EXAMPLE_DIR} 向上查找）",
    )


def _build_app(
    cfg,
    skills_root: Path,
    mcp_tools: list,
) -> tuple[AgentApp, ExamplePrintTiming]:
    _SANDBOX.mkdir(parents=True, exist_ok=True)
    _SEARCH_SCRATCH.mkdir(parents=True, exist_ok=True)
    timing = ExamplePrintTiming()
    listener, _ = create_print_listener(
        model=cfg.model,
        base_url=cfg.base_url,
        timing=timing,
    )
    app = AgentApp(
        _SANDBOX,
        harness_enabled=False,
        planning_enabled=False,
        skill_roots={"skills": skills_root},
        rule_paths=[_RULE_PATH, _write_workspace_rule()],
        api_key=cfg.api_key,
        model=cfg.model,
        base_url=cfg.base_url,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        thinking_enabled=cfg.thinking_enabled,
        memory_api_key=cfg.api_key,
        memory_model=cfg.model,
        memory_base_url=cfg.base_url,
        listeners=listener,
    )
    app.set_shared_extra_tools(mcp_tools)
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
    print(f"{timing.tag()} 联网搜索工作区：{_SEARCH_SCRATCH}")
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


async def _run_demo() -> int:
    skills_root = _resolve_skills_root()
    print(f"技能根：{skills_root}")
    ensure_example_mcp_debug_logs(_SEARCH_SCRATCH)
    ai_log = os.environ.get("AI_AGENT_MCP_DEBUG_LOG", "")
    print(f"MCP 调试日志（ai_agent）：{ai_log}")
    print(f"MCP 调试日志（cursor_cli）：{_SEARCH_SCRATCH / 'cursor_cli.mcp.stderr.log'}")
    cfg = load_llm_config(_EXAMPLE_DIR)
    tools, loader = await prepare_and_load_mcp_with_debug(
        _EXAMPLE_DIR,
        _SEARCH_SCRATCH,
    )
    try:
        app, timing = _build_app(cfg, skills_root, tools)
        return await _run_script(app, timing)
    finally:
        await loader.close()


async def _run() -> int:
    _SEARCH_SCRATCH.mkdir(parents=True, exist_ok=True)
    example_step("步骤 1/3：加载 mcp.json、列出工具并取时")
    code = await run_mcp_check(_EXAMPLE_DIR, scratch_dir=_SEARCH_SCRATCH)
    if code != 0:
        return code

    example_step("步骤 2/3：探测 cursor_cli__run_cursor_agent")
    code = await run_mcp_probe(_EXAMPLE_DIR, _SEARCH_SCRATCH)
    if code != 0:
        return code

    example_step("步骤 3/3：LLM 联网搜索演示")
    return await _run_demo()


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
