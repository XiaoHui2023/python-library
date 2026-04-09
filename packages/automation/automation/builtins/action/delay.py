from __future__ import annotations
from typing import ClassVar, TYPE_CHECKING
import asyncio
from pydantic import Field
from automation.core import Action

if TYPE_CHECKING:
    from automation.renderer import Renderer


class DelayAction(Action):
    _type: ClassVar[str] = "delay"
    _abstract: ClassVar[bool] = False

    seconds: float = Field(ge=0, description="等待秒数")

    async def execute(self, renderer: Renderer) -> None:
        await asyncio.sleep(self.seconds)