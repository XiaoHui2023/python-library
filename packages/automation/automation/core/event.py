from __future__ import annotations
from typing import Any, Callable, ClassVar, TYPE_CHECKING

import logging
from .base import BaseAutomation
from registry import Registry
import inspect
import asyncio
from pydantic import PrivateAttr

if TYPE_CHECKING:
    from automation.hub import Hub

logger = logging.getLogger(__name__)
NAME_SPACE = "event"

event_registry = Registry(NAME_SPACE)


class Event(BaseAutomation):
    _abstract: ClassVar[bool] = True
    _registry: ClassVar[Registry] = event_registry

    _on_fire: list[Callable[[], Any]] = PrivateAttr(default_factory=list)
    _on_error: Callable[[Exception], Any] | None = PrivateAttr(default=None)

    async def fire(self):
        tasks = []
        for callback in self._on_fire:
            try:
                result = callback()
            except Exception as e:
                await self._handle_error(e)
                continue
            if inspect.isawaitable(result):
                tasks.append(result)
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    await self._handle_error(result)

    async def _handle_error(self, error: Exception) -> None:
        logger.error("Event callback failed: %s", error, exc_info=error)
        if self._on_error is not None:
            try:
                err_result = self._on_error(error)
                if inspect.isawaitable(err_result):
                    await err_result
            except Exception:
                logger.exception("Error handler raised an exception")

    def set_error_handler(self, handler: Callable[[Exception], Any] | None) -> None:
        self._on_error = handler

    def add_listener(self, callback: Callable[[], Any]) -> None:
        if callback not in self._on_fire:
            self._on_fire.append(callback)

    def remove_listener(self, callback: Callable[[], Any]) -> None:
        try:
            self._on_fire.remove(callback)
        except ValueError:
            pass