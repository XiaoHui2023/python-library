import asyncio
from enum import StrEnum
from typing import Any, Literal, overload
from .core import Entity, Event, Condition, Action, Trigger, BaseAutomation
from .listener import AutomationListener

class State(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"


class Hub:
    """所有模块共享的核心状态容器"""

    SECTIONS = ("entities", "events", "conditions", "actions", "triggers")

    def __init__(self) -> None:
        self.entities: dict[str, Entity] = {}
        self.events: dict[str, Event] = {}
        self.conditions: dict[str, Condition] = {}
        self.actions: dict[str, Action] = {}
        self.triggers: dict[str, Trigger] = {}

        self.state: State = State.IDLE
        self.stop_event: asyncio.Event = asyncio.Event()
        self.config: dict[str, Any] = {}
        self.listener: AutomationListener = AutomationListener()


    @overload
    def section(self, name: Literal["entities"]) -> dict[str, Entity]: ...
    @overload
    def section(self, name: Literal["events"]) -> dict[str, Event]: ...
    @overload
    def section(self, name: Literal["conditions"]) -> dict[str, Condition]: ...
    @overload
    def section(self, name: Literal["actions"]) -> dict[str, Action]: ...
    @overload
    def section(self, name: Literal["triggers"]) -> dict[str, Trigger]: ...
    @overload
    def section(self, name: str) -> dict[str, BaseAutomation]: ...

    def section(self, name: str) -> dict[str, BaseAutomation]:
        if name not in self.SECTIONS:
            raise KeyError(f"Unknown section: {name!r}")
        return getattr(self, name)