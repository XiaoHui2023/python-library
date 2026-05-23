from __future__ import annotations

import logging

from pydantic import Field

from automation.core.action import Action
from automation.core.renderer import Renderer

logger = logging.getLogger(__name__)


class LogAction(Action):
    """将一条信息写入日志。"""

    info: str = Field(description="日志正文；字符串值在运行期经表达式渲染器求值。")

    @property
    def display_label(self) -> str:
        return "log"

    @property
    def log_params(self) -> dict[str, str]:
        return {"info": self.info}

    async def execute(self, renderer: Renderer) -> None:
        text = self.info
        if "{" in text or "}" in text:
            text = str(renderer(text))
        logger.info(text)
