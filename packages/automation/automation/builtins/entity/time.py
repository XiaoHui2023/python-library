from __future__ import annotations
from datetime import datetime
from typing import ClassVar
from automation.core import Entity
from automation.core.entity import AttributeInfo


class TimeEntity(Entity):
    _abstract: ClassVar[bool] = False
    _type: ClassVar[str] = "time"

    _attributes: ClassVar[tuple[AttributeInfo, ...]] = (
        AttributeInfo("hour", "int", "当前小时 (0-23)", readonly=True),
        AttributeInfo("minute", "int", "当前分钟 (0-59)", readonly=True),
        AttributeInfo("second", "int", "当前秒 (0-59)", readonly=True),
        AttributeInfo("weekday", "int", "星期几 (0=周一, 6=周日)", readonly=True),
    )

    @property
    def hour(self) -> int:
        return datetime.now().hour

    @property
    def minute(self) -> int:
        return datetime.now().minute

    @property
    def second(self) -> int:
        return datetime.now().second

    @property
    def weekday(self) -> int:
        return datetime.now().weekday()