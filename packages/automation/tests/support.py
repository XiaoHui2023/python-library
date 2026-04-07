"""测试辅助：确保 builtins 注册并完成异步 load。"""

from __future__ import annotations

import asyncio

import automation  # noqa: F401 — 注册内置 Action/Event/Condition 等

from automation import loader
from automation.hub import Hub


async def load_hub(config: dict) -> Hub:
    hub = Hub()
    await loader.load(hub, config)
    return hub


def run_hub(config: dict) -> Hub:
    return asyncio.run(load_hub(config))
