from __future__ import annotations
import logging
import time
from typing import ClassVar, Literal, TYPE_CHECKING
import asyncio
from pydantic import Field, PrivateAttr
from automation.core.base import BaseAutomation
from automation.core.event import Event
from automation.core.condition import Condition
from automation.core.action import Action
from registry import Registry

if TYPE_CHECKING:
    from automation.hub import Hub

logger = logging.getLogger(__name__)
NAME_SPACE = "trigger"

trigger_registry = Registry(NAME_SPACE)

class Trigger(BaseAutomation):
    _type: ClassVar[str] = "trigger"
    _registry: ClassVar[Registry] = trigger_registry
    _abstract: ClassVar[bool] = False

    event: str = Field(description="事件名称")
    conditions: list[str] = Field(default_factory=list, description="条件名称列表")
    actions: list[str] = Field(default_factory=list, description="动作名称列表")
    mode: Literal["skip", "queue"] = Field(default="skip", description="并发策略")

    _event: Event | None = PrivateAttr(default=None)
    _conditions: list[Condition] = PrivateAttr(default_factory=list)
    _actions: list[Action] = PrivateAttr(default_factory=list)
    _lock: asyncio.Lock = PrivateAttr(default_factory=asyncio.Lock)
    _queue: asyncio.Queue[None] = PrivateAttr(default_factory=lambda: asyncio.Queue())
    _worker_task: asyncio.Task | None = PrivateAttr(default=None)
    _running_task: asyncio.Task | None = PrivateAttr(default=None)

    async def on_validate(self, hub: Hub) -> None:
        try:
            self._event = hub.events[self.event]
        except KeyError as e:
            raise ValueError(f"Event {self.event!r} not found") from e

        try:
            self._conditions = [hub.conditions[name] for name in self.conditions]
        except KeyError as e:
            raise ValueError(f"Condition {e.args[0]!r} not found") from e

        try:
            self._actions = [hub.actions[name] for name in self.actions]
        except KeyError as e:
            raise ValueError(f"Action {e.args[0]!r} not found") from e

        if not self._actions:
            raise ValueError("At least one action is required")

    async def on_activate(self, hub: Hub) -> None:
        if self._event is not None:
            self._event.remove_listener(self.run)
        if self.event not in hub.events:
            raise ValueError(
                f"Event {self.event!r} not found; was on_validate() called?"
            )
        self._event = hub.events[self.event]
        self._event.add_listener(self.run)

    async def on_start(self) -> None:
        if self.mode == "queue":
            self._worker_task = asyncio.create_task(self._queue_worker())

    async def on_stop(self) -> None:
        for task in (self._worker_task, self._running_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    async def run(self) -> None:
        ln = self._hub.listener if self._hub else None
        match self.mode:
            case "skip":
                if self._lock.locked():
                    if ln:
                        ln.on_trigger_skipped(self.instance_name)
                    return
                self._running_task = asyncio.create_task(self._skip_run())
                await self._running_task
            case "queue":
                await self._queue.put(None)

    async def _skip_run(self) -> None:
        async with self._lock:
            await self._execute()

    async def _queue_worker(self) -> None:
        while True:
            await self._queue.get()
            try:
                await self._execute()
            except Exception:
                logger.exception("Trigger %r execution failed", self.instance_name)
            finally:
                self._queue.task_done()

    async def _execute(self) -> None:
        ln = self._hub.listener if self._hub else None
        t0 = time.perf_counter()

        if ln:
            ln.on_trigger_started(self.instance_name)

        for condition in self._conditions:
            passed = await condition.check()
            if ln:
                ln.on_condition_checked(
                    self.instance_name, condition.instance_name, passed
                )
            if not passed:
                if ln:
                    ln.on_trigger_aborted(
                        self.instance_name, condition.instance_name
                    )
                return

        for action in self._actions:
            if ln:
                ln.on_action_started(self.instance_name, action.instance_name)
            t1 = time.perf_counter()
            try:
                await action.run()
            except Exception as e:
                if ln:
                    ln.on_action_error(
                        self.instance_name, action.instance_name, e
                    )
                    ln.on_trigger_error(self.instance_name, e)
                raise
            if ln:
                ln.on_action_completed(
                    self.instance_name,
                    action.instance_name,
                    time.perf_counter() - t1,
                )

        if ln:
            ln.on_trigger_completed(
                self.instance_name, time.perf_counter() - t0
            )