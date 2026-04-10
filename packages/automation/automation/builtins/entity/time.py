from __future__ import annotations
from datetime import datetime
from typing import ClassVar
from automation.core import Entity


class TimeEntity(Entity):
    _abstract: ClassVar[bool] = False
    _type: ClassVar[str] = "time"

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