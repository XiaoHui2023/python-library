from __future__ import annotations
from typing import ClassVar

from .base import BaseAutomation
from registry import Registry

NAME_SPACE = "entity"

entity_registry = Registry(NAME_SPACE)

class Entity(BaseAutomation):
    _abstract: ClassVar[bool] = True
    _registry: ClassVar[Registry] = entity_registry