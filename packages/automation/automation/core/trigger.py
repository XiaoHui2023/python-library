from __future__ import annotations
import logging
import time
from typing import ClassVar, Literal, TYPE_CHECKING
import asyncio
from pydantic import Field, PrivateAttr
from .base import BaseAutomation
from .event import Event
from .event_context import EventContext
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
    conditions: list[str] = Field(
        default_factory=list,
        description="条件表达式列表",
    )
    actions: list[dict] = Field(
        default_factory=list,
        description="动作规格列表",
    )
    mode: Literal["skip", "queue"] = Field(
        default="skip", description="并发策略"
    )

    _event: Event | None = PrivateAttr(default=None)
    _lock: asyncio.Lock = PrivateAttr(default_factory=asyncio.Lock)
    _queue: asyncio.Queue[EventContext | None] = PrivateAttr(
        default_factory=asyncio.Queue
    )
    _worker_task: asyncio.Task | None = PrivateAttr(default=None)
    _running_task: asyncio.Task | None = PrivateAttr(default=None)

    async def on_validate(self, hub: Hub) -> None:
        if self.event not in hub.events:
            raise ValueError(f"Event {self.event!r} not found")
        self._event = hub.events[self.event]

        for expr in self.conditions:
            hub.renderer.validate_expr(expr)

        from automation.executor import validate_action_spec
        for spec in self.actions:
            validate_action_spec(spec, hub)

        if not self.actions:
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

    async def run(self, context: EventContext | None = None) -> None:
        match self.mode:
            case "skip":
                if self._lock.locked():
                    self._hub.notify("on_trigger_skipped", self.instance_name)
                    return
                self._running_task = asyncio.create_task(
                    self._skip_run(context)
                )
                await self._running_task
            case "queue":
                await self._queue.put(context)

    async def _skip_run(self, context: EventContext | None = None) -> None:
        async with self._lock:
            await self._execute(context)

    async def _queue_worker(self) -> None:
        while True:
            context = await self._queue.get()
            try:
                await self._execute(context)
            except Exception:
                logger.exception(
                    "Trigger %r execution failed", self.instance_name
                )
            finally:
                self._queue.task_done()

    async def _execute(self, context: EventContext | None = None) -> None:
        from automation.executor import execute_action_spec

        hub = self._hub
        t0 = time.perf_counter()

        hub.notify("on_trigger_started", self.instance_name)

        renderer = hub.renderer.derive(
            "event", "local", context.data if context else {}
        )

        for expr in self.conditions:
            passed = renderer.eval_bool(expr)
            hub.notify("on_condition_checked", self.instance_name, expr, passed)
            if not passed:
                hub.notify("on_trigger_aborted", self.instance_name, expr)
                return

        for spec in self.actions:
            action_type = spec.get("type", "?")
            spec_params = {k: v for k, v in spec.items() if k != "type"}
            hub.notify("on_action_started", self.instance_name, action_type, params=spec_params)
            t1 = time.perf_counter()
            try:
                await execute_action_spec(spec, renderer, hub)
            except Exception as e:
                hub.notify("on_action_error", self.instance_name, action_type, e)
                hub.notify("on_trigger_error", self.instance_name, e)
                raise
            elapsed = time.perf_counter() - t1
            hub.notify("on_action_completed", self.instance_name, action_type, elapsed, params=spec_params)

        hub.notify(
            "on_trigger_completed",
            self.instance_name,
            time.perf_counter() - t0,
        )