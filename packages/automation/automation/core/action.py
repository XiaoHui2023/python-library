from __future__ import annotations
from typing import ClassVar

from .base import BaseAutomation
from abc import abstractmethod
from registry import Registry

NAME_SPACE = "action"

action_registry = Registry(NAME_SPACE)


class Action(BaseAutomation):
    _abstract: ClassVar[bool] = True
    _registry: ClassVar[Registry] = action_registry

    @abstractmethod
    async def run(self) -> None:
        pass