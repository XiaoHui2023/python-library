from __future__ import annotations

import asyncio

from pydantic import Field

from automation.core.action import Action
from automation.core.renderer import Renderer


class DelayAction(Action):
    """异步等待指定秒数。"""

    seconds: float = Field(default=0.0, description="等待秒数。")

    @property
    def display_label(self) -> str:
        return "delay"

    @property
    def log_params(self) -> dict[str, float]:
        return {"seconds": self.seconds}

    async def execute(self, renderer: Renderer) -> None:
        await asyncio.sleep(self.seconds)
