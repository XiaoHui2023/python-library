from __future__ import annotations
from typing import Any, Callable, ClassVar

from .base import BaseAutomation
from registry import Registry
import inspect
import asyncio
from pydantic import PrivateAttr

NAME_SPACE = "event"

event_registry = Registry(NAME_SPACE)

class Event(BaseAutomation):
    _abstract: ClassVar[bool] = True
    _registry: ClassVar[Registry] = event_registry

    _on_fire: list[Callable[[], Any]] = PrivateAttr(default_factory=list)
    """事件触发回调"""

    async def fire(self):
        """触发事件"""
        tasks = []
        for callback in self._on_fire:
            result = callback()
            if inspect.isawaitable(result):
                tasks.append(result)
        if tasks:
            await asyncio.gather(*tasks)

    def on_fire(self, callback):
        if callback not in self._on_fire:
            self._on_fire.append(callback)