from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from ai_agent import AgentApp, RunInputPacket

from examples._support.demo_sandbox import clear_demo_sessions, session_ids_in_script
from examples._support.llm_config import load_llm_config
from examples._support.load_example_mcp import prepare_and_load_mcp
from examples._support.print_listener import create_print_listener
from examples._support.print_timing import ExamplePrintTiming

_EXAMPLE_DIR = Path(__file__).resolve().parent
_SANDBOX = _EXAMPLE_DIR / ".sandbox"
_RULE_PATH = _EXAMPLE_DIR / "rules" / "assistant.md"
_FIXTURES = _EXAMPLE_DIR / "fixtures"
_DEMO_SESSION = "demo"

_ScriptStep = tuple[str, str, str, bool, tuple[str, ...]]

_SCRIPT_STEPS: tuple[_ScriptStep, ...] = (
    (
        "demo",
        "用户",
        "",
        True,
        (str(_FIXTURES / "note.txt"),),
    ),
    (
        "demo",
        "用户",
        "这是什么？",
        False,
        (str(_FIXTURES / "sample.png"),),
    ),
)


def _write_workspace_rule() -> Path:
    path = _EXAMPLE_DIR / "rules" / "workspace.md"
    harness_rel = f"sessions/{_DEMO_SESSION}/harness"
    path.write_text(
        "## 本示例 MCP 工作区\n\n"
        f"调用 **cursor_cli__run_cursor_agent** 时 **workspace** 填：`{harness_rel}`\n"
        "（相对 mcp.json 的 **cwd**，即本示例 `.sandbox` 目录）。\n"
        "**image_paths** / **context_paths** 填相对该 workspace 的路径（如 `incoming/photo.png`）。\n",
        encoding="utf-8",
    )
    return path


def _build_app(cfg, mcp_tools: list) -> tuple[AgentApp, ExamplePrintTiming]:
    _SANDBOX.mkdir(parents=True, exist_ok=True)
    timing = ExamplePrintTiming()
    listener, _ = create_print_listener(
        model=cfg.model,
        base_url=cfg.base_url,
        timing=timing,
    )
    app = AgentApp(
        _SANDBOX,
        rule_paths=[_RULE_PATH, _write_workspace_rule()],
        api_key=cfg.api_key,
        model=cfg.model,
        base_url=cfg.base_url,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        thinking_enabled=cfg.thinking_enabled,
        harness_enabled=True,
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
    input_files: tuple[str, ...] = (),
) -> tuple[str, tuple[str, ...]]:
    timing.reset()
    output = await app.run(
        RunInputPacket(
            user_name=user_name,
            session_id=session_id,
            request=request,
            input_files=input_files,
            clear=clear,
        ),
    )
    return output.answer.strip(), output.output_files


async def _run_script(app: AgentApp, timing: ExamplePrintTiming) -> int:
    demo_sessions = session_ids_in_script(
        tuple(step[:4] for step in _SCRIPT_STEPS),
    )
    clear_demo_sessions(_SANDBOX, demo_sessions)
    print(f"{timing.tag()} 演示前已清空会话: {', '.join(demo_sessions)}")
    print()
    ok = True
    for session_id, user_name, request, clear, input_files in _SCRIPT_STEPS:
        timing.reset()
        print(f"{timing.tag()} --- 会话 {session_id} | 用户 {user_name} ---")
        label = request.strip() or "（仅附件，无文字）"
        print(f"{timing.tag()} > {label}")
        if input_files:
            print(f"{timing.tag()} 附件: {', '.join(input_files)}")
        answer, out_files = await _one_turn(
            app,
            timing,
            session_id=session_id,
            user_name=user_name,
            request=request,
            clear=clear,
            input_files=input_files,
        )
        print(f"{timing.tag()} 回合结束")
        if out_files:
            print(f"{timing.tag()} 输出文件: {', '.join(out_files)}")
        print()
        if not answer:
            ok = False
    return 0 if ok else 1


async def _run() -> int:
    cfg = load_llm_config(_EXAMPLE_DIR)
    tools, loader = await prepare_and_load_mcp(_EXAMPLE_DIR)
    try:
        app, timing = _build_app(cfg, tools)
        return await _run_script(app, timing)
    finally:
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
