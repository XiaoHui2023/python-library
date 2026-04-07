from typing import ClassVar
import logging
from pydantic import Field
from automation.core import Action

logger = logging.getLogger(__name__)

class LogAction(Action):
    _type: ClassVar[str] = "log"
    _abstract: ClassVar[bool] = False

    info: str = Field(description="日志内容")

    async def run(self) -> None:
        logger.info(self.info)