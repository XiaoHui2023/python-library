from __future__ import annotations



import asyncio

import logging

import time

from typing import Literal



from pydantic import Field, PrivateAttr



from automation.core.action import Action, InstrumentedActionRun

from automation.core.base import BaseAutomation

from automation.core.event import Event, EventContext

from automation.core.registry_catalog import TRIGGER_NAMESPACE, trigger_registry

from automation.listener.events import (

    ConditionChecked,

    TriggerAborted,

    TriggerCompleted,

    TriggerError,

    TriggerSkipped,

    TriggerStarted,

)



logger = logging.getLogger(__name__)





class Trigger(BaseAutomation):

    """将「某事件触发」映射为「在满足额外条件下执行一串动作」。"""



    event: str = Field(description="事件名称")

    conditions: list[str] = Field(

        default_factory=list,

        description="条件表达式列表",

    )

    actions: list[Action] = Field(

        default_factory=list,

        description="事件触发后要依次执行的动作实例列表",

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

    _instrumented_steps: list[InstrumentedActionRun] = PrivateAttr(

        default_factory=list

    )



    async def on_build(self) -> None:

        ctx = self._ctx

        if self.event in ctx.events:

            self._event = ctx.events[self.event]



        steps: list[InstrumentedActionRun] = []

        for i, action in enumerate(self.actions):

            inst = InstrumentedActionRun.wrap(

                instance_name=f"{self.instance_name}._step{i}",

                context=ctx,

                inner=action,

                trigger_name=self.instance_name,

            )

            await inst.build_phase()

            steps.append(inst)

        self._instrumented_steps = steps



    async def on_validate(self) -> None:

        ctx = self._ctx

        if self.event not in ctx.events:

            raise ValueError(f"Event {self.event!r} not found")

        self._event = ctx.events[self.event]



        for expr in self.conditions:

            ctx.create_renderer()(expr)



        if not self.actions:

            raise ValueError("At least one action is required")



        for inst in self._instrumented_steps:

            await inst.validate_phase()



    async def on_activate(self) -> None:

        ctx = self._ctx

        if self._event is not None:

            self._ctx.remove_event_fire_handler(self.event, self.run)

        if self.event not in ctx.events:

            raise ValueError(f"Event {self.event!r} not found")

        self._event = ctx.events[self.event]

        self._ctx.add_event_fire_handler(self.event, self.run)



    async def on_inactive(self) -> None:

        self._ctx.remove_event_fire_handler(self.event, self.run)



    async def on_run(self, *, closing: bool = False) -> None:

        if closing:

            for task in (self._worker_task, self._running_task):

                if task and not task.done():

                    task.cancel()

                    try:

                        await task

                    except asyncio.CancelledError:

                        pass

            return

        if self.mode == "queue":

            self._worker_task = asyncio.create_task(self._queue_worker())



    async def run(self, context: EventContext | None = None) -> None:

        match self.mode:

            case "skip":

                if self._lock.locked():

                    self._ctx.emit(TriggerSkipped(self.instance_name))

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

        ctx = self._ctx

        t0 = time.perf_counter()



        ctx.emit(TriggerStarted(self.instance_name))



        renderer = ctx.create_renderer().derive(context.data if context else {})



        for expr in self.conditions:

            passed = bool(renderer(expr))

            ctx.emit(ConditionChecked(self.instance_name, expr, passed))

            if not passed:

                ctx.emit(TriggerAborted(self.instance_name, expr))

                return



        for inst in self._instrumented_steps:

            try:

                await inst.run_phased_execute(renderer)

            except Exception as e:

                ctx.emit(TriggerError(self.instance_name, e))

                raise



        ctx.emit(

            TriggerCompleted(self.instance_name, time.perf_counter() - t0)

        )





Trigger.registered_kind = TRIGGER_NAMESPACE

trigger_registry.register(TRIGGER_NAMESPACE, Trigger)

