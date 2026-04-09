import asyncio
from enum import StrEnum
from typing import Any, Literal, overload
from .core import Entity, Event, Trigger, BaseAutomation
from .core.composite_action import CompositeAction
from .renderer import Renderer
from .listener import BaseListener


class State(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"


class Hub:
    """所有模块共享的核心状态容器"""

    SECTIONS = ("entities", "events", "actions", "triggers")

    def __init__(self) -> None:
        self.entities: dict[str, Entity] = {}
        self.events: dict[str, Event] = {}
        self.actions: dict[str, CompositeAction] = {}
        self.triggers: dict[str, Trigger] = {}

        self.state: State = State.IDLE
        self.stop_event: asyncio.Event = asyncio.Event()
        self.config: dict[str, Any] = {}
        self.listeners: list[BaseListener] = []
        self.renderer: Renderer = Renderer(self)

    AUTOMATION_SECTIONS = ("entities", "events", "triggers")

    @overload
    def section(self, name: Literal["entities"]) -> dict[str, Entity]: ...
    @overload
    def section(self, name: Literal["events"]) -> dict[str, Event]: ...
    @overload
    def section(self, name: Literal["triggers"]) -> dict[str, Trigger]: ...
    @overload
    def section(self, name: str) -> dict[str, BaseAutomation]: ...

    def section(self, name: str) -> dict[str, BaseAutomation]:
        if name not in self.AUTOMATION_SECTIONS:
            raise KeyError(f"Unknown automation section: {name!r}")
        return getattr(self, name)
        
    def notify(self, method: str, *args, **kwargs) -> None:
        for ln in self.listeners:
            getattr(ln, method)(*args, **kwargs)