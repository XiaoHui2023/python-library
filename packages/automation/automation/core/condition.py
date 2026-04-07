from __future__ import annotations
from typing import ClassVar

from .base import BaseAutomation
from registry import Registry
from abc import abstractmethod

NAME_SPACE = "condition"

condition_registry = Registry(NAME_SPACE)


class Condition(BaseAutomation):
    _abstract: ClassVar[bool] = True
    _registry: ClassVar[Registry] = condition_registry

    @abstractmethod
    async def check(self) -> bool:
        raise NotImplementedError