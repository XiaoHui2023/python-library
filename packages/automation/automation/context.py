from __future__ import annotations

import asyncio

from pydantic import BaseModel, ConfigDict, Field


class Context(BaseModel):
    """各模块共享的运行时状态。"""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )

    stop_event: asyncio.Event = Field(
        default_factory=asyncio.Event,
        description="主循环停止信号；run 启动时会替换为新实例",
    )
    is_running: bool = Field(
        default=False,
        description="主循环是否正在运行",
    )
