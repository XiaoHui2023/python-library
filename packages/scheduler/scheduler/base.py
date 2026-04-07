import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Callable, Any

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

Handler = Callable[[], Any]

logger = logging.getLogger(__name__)


class BaseScheduler(BaseModel, ABC):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
        validate_assignment=True,
    )

    immediate: bool = Field(False, description="是否立即执行")
    max_runs: int | None = Field(None,description="最大触发次数，不填则表示不限制")

    _handlers: list[Handler] = PrivateAttr(default_factory=list)
    _runner_task: asyncio.Task | None = PrivateAttr(None)
    _stop_event: asyncio.Event = PrivateAttr(default_factory=asyncio.Event)
    _running: bool = PrivateAttr(False)
    _last_fire_at: datetime | None = PrivateAttr(None)
    _run_count: int = PrivateAttr(0)
    _first_tick: bool = PrivateAttr(True)

    @model_validator(mode="after")
    def _validate_max_runs(self):
        if self.max_runs is not None and self.max_runs < 1:
            raise ValueError("max_runs must be >= 1 when set")
        return self

    def _next_delay(self) -> float:
        """距离下次触发的推荐等待秒数，子类可覆盖以实现动态间隔"""
        return 0.5

    def add(self, fn: Handler):
        self._handlers.append(fn)
        return fn

    def __call__(self, fn: Handler):
        return self.add(fn)

    async def start(self):
        if self._runner_task and not self._runner_task.done():
            return self

        loop = asyncio.get_running_loop()
        self._stop_event.clear()
        self._first_tick = True
        self._run_count = 0
        self._last_fire_at = None if self.immediate else datetime.now()
        self._runner_task = loop.create_task(self._serve())
        return self

    async def wait(self):
        if self._runner_task is None:
            raise RuntimeError("scheduler has not been started")
        await self._runner_task
        return self

    async def stop(self):
        self._stop_event.set()
        return self

    async def run(self):
        await self.start()
        await self.wait()
        return self

    async def _serve(self):
        self._running = True
        try:
            while not self._stop_event.is_set():
                if self._should_fire():
                    await self._fire_all()

                self._first_tick = False

                delay = max(self._next_delay(), 0.1)
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=delay,
                    )
                except asyncio.TimeoutError:
                    pass
        finally:
            self._running = False

    def _should_fire(self) -> bool:
        if not self._handlers:
            return False

        if self._first_tick:
            return self.immediate

        return self._condition()

    async def _fire_all(self):
        self._last_fire_at = datetime.now()
        self._run_count += 1

        results = await asyncio.gather(
            *(self._invoke(fn) for fn in self._handlers),
            return_exceptions=True,
        )

        for fn, result in zip(self._handlers, results):
            if isinstance(result, Exception):
                logger.exception("scheduler handler failed: %r", fn, exc_info=result)

        if self.max_runs is not None and self._run_count >= self.max_runs:
            self._stop_event.set()

    async def _invoke(self, fn: Handler):
        if asyncio.iscoroutinefunction(fn):
            await fn()
        else:
            await asyncio.to_thread(fn)

    @abstractmethod
    def _condition(self) -> bool: ...