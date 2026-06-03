from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from ai_agent import AgentApp, RunInputPacket

from examples._support.demo_sandbox import clear_demo_sessions, session_ids_in_script
from examples._support.llm_config import load_llm_config
from examples._support.print_listener import create_print_listener
from examples._support.print_timing import ExamplePrintTiming

_EXAMPLE_DIR = Path(__file__).resolve().parent
_SANDBOX = _EXAMPLE_DIR / ".sandbox"
_RULE_PATH = _EXAMPLE_DIR / "rules" / "assistant.md"

_ScriptStep = tuple[str, str, str, bool]

# 记忆与会话隔离：work 记住 Alice → 回忆 → private 不应串会话 → 回到 work
_SCRIPT_STEPS: tuple[_ScriptStep, ...] = (
    ("work", "Alice", "我叫 Alice，请记住我的名字。", False),
    ("work", "Alice", "我叫什么名字？", False),
    ("private", "Bob", "我叫什么名字？", False),
    ("work", "Alice", "再确认一下，我叫什么？", False),
)


def _build_app(cfg) -> tuple[AgentApp, ExamplePrintTiming]:
    _SANDBOX.mkdir(parents=True, exist_ok=True)
    timing = ExamplePrintTiming()
    listener, _ = create_print_listener(
        model=cfg.model,
        base_url=cfg.base_url,
        timing=timing,
    )
    app = AgentApp(
        _SANDBOX,
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
    cfg = load_llm_config(_EXAMPLE_DIR)
    app, timing = _build_app(cfg)
    return await _run_script(app, timing)


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
