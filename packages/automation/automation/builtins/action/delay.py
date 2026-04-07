from typing import ClassVar
import asyncio

from pydantic import Field

from automation.core import Action


class DelayAction(Action):
    _type: ClassVar[str] = "delay"
    _abstract: ClassVar[bool] = False

    seconds: float = Field(ge=0, description="等待秒数")

    async def run(self) -> None:
        await asyncio.sleep(self.seconds)