from __future__ import annotations
from datetime import datetime
from typing import ClassVar
from automation.core import Entity


class TimeEntity(Entity):
    _abstract: ClassVar[bool] = False
    _type: ClassVar[str] = "time"

    @property
    def hour(self) -> int:
        """当前小时 (0-23)"""
        return datetime.now().hour

    @property
    def minute(self) -> int:
        """当前分钟 (0-59)"""
        return datetime.now().minute

    @property
    def second(self) -> int:
        """当前秒 (0-59)"""
        return datetime.now().second

    @property
    def weekday(self) -> int:
        """星期几 (0=周一, 6=周日)"""
        return datetime.now().weekday()