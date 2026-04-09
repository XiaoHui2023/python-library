from __future__ import annotations
from typing import ClassVar, TYPE_CHECKING
import logging
from pydantic import Field
from automation.core import Action

if TYPE_CHECKING:
    from automation.renderer import Renderer

logger = logging.getLogger(__name__)


class LogAction(Action):
    _type: ClassVar[str] = "log"
    _abstract: ClassVar[bool] = False

    info: str = Field(description="日志内容")

    async def execute(self, renderer: Renderer) -> None:
        logger.info(self.info)