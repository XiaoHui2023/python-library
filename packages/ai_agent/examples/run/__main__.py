from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from ai_agent import Agent, ChatMessage

from examples._support.llm_config import load_llm_config
from examples._support.print_listener import create_print_listener
from examples._support.print_timing import ExamplePrintTiming

_EXAMPLE_DIR = Path(__file__).resolve().parent
_RULE_PATH = _EXAMPLE_DIR / "rules" / "assistant.md"
_DEMO_USER = "用一两句话介绍你自己。"


async def _run() -> int:
    cfg = load_llm_config(_EXAMPLE_DIR)
    timing = ExamplePrintTiming()
    listener, _ = create_print_listener(
        model=cfg.model,
        base_url=cfg.base_url,
        timing=timing,
    )
    agent = Agent(
        api_key=cfg.api_key,
        model=cfg.model,
        base_url=cfg.base_url,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        rule_paths=[_RULE_PATH],
        listeners=listener,
    )

    timing.reset()
    print(f"{timing.tag()} > {_DEMO_USER}")
    output = await agent.run(
        messages=[ChatMessage(role="user", content=_DEMO_USER)],
    )
    return 0 if output.strip() else 1


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
