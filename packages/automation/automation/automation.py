from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from automation.context import Context

logger = logging.getLogger(__name__)

PayloadT = TypeVar("PayloadT")
AutomationHandler = Callable[[PayloadT], Awaitable[None]]

_instances: list[Automation[Any]] = []


class Automation(BaseModel, Generic[PayloadT]):
    """自动化：构建钩子、带门禁的运行管线，并按并发策略通知监听者。"""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )

    name: str = Field(..., description="实例名")
    ctx: Context | None = Field(
        default=None,
        exclude=True,
        repr=False,
        description="运行时上下文；由 runtime.start() 注入，实例化时可省略",
    )
    mode: Literal["skip", "queue"] = Field(
        default="skip",
        description="skip 表示忙时跳过；queue 表示排队依次通知",
    )
    is_running: bool = Field(
        default=False,
        description="是否正在通知本次触发的监听者",
    )
    interval: float = Field(
        default=1.0,
        gt=0,
        description="持续调度循环的基础间隔（秒）；节拍间等待可被 stop_event 提前结束",
    )

    _handlers: list[AutomationHandler[PayloadT]] = PrivateAttr(default_factory=list)
    _lock: asyncio.Lock = PrivateAttr(default_factory=asyncio.Lock)
    _queue: asyncio.Queue[PayloadT] = PrivateAttr(default_factory=asyncio.Queue)
    _worker_task: asyncio.Task[None] | None = PrivateAttr(default=None)

    def register(
        self,
        func: AutomationHandler[PayloadT],
    ) -> AutomationHandler[PayloadT]:
        self._handlers.append(func)
        return func

    def __call__(self, func: AutomationHandler[PayloadT]) -> AutomationHandler[PayloadT]:
        return self.register(func)

    def model_post_init(self, __context: object) -> None:
        _instances.append(self)

    def _require_ctx(self) -> Context:
        if self.ctx is None:
            raise RuntimeError(
                f"自动化 {self.name!r} 尚未绑定 Context，请先调用 automation.start()",
            )
        return self.ctx

    async def on_init(self) -> None:
        if self.mode == "queue" and self._worker_task is None:
            self._worker_task = asyncio.create_task(self._queue_worker())
        await self.on_build()

    async def on_build(self) -> None:
        pass

    async def should_run(self) -> bool:
        return True

    async def run(self, payload: PayloadT) -> None:
        self._require_ctx()
        if not await self.should_run():
            return
        if self.mode == "queue":
            await self._queue.put(payload)
            return
        if self.mode == "skip":
            if self._lock.locked():
                return
            async with self._lock:
                await self._execute(payload)

    async def _execute(self, payload: PayloadT) -> None:
        self.is_running = True
        try:
            await asyncio.gather(
                *(
                    self._run_handler(handler, payload)
                    for handler in list(self._handlers)
                ),
            )
        finally:
            self.is_running = False

    async def _run_handler(
        self,
        handler: AutomationHandler[PayloadT],
        payload: PayloadT,
    ) -> None:
        try:
            await handler(payload)
        except Exception:
            logger.exception("自动化 %r 监听函数执行失败", self.name)

    async def on_tick(self) -> None:
        """每个调度节拍调用，默认可为空。

        若在此方法内自行长时间阻塞，须周期性检查上下文上的停止事件，
        或改用可被 stop 打断的等待，否则会延迟进程退出。
        """
        return

    async def run_timing_loop(self) -> None:
        """持续运行：循环调用 on_tick，直至 ctx.stop_event 置位。"""
        ctx = self._require_ctx()
        while not ctx.stop_event.is_set():
            await self.on_tick()
            if ctx.stop_event.is_set():
                break
            try:
                await asyncio.wait_for(
                    ctx.stop_event.wait(),
                    timeout=self.interval,
                )
                break
            except asyncio.TimeoutError:
                continue

    async def _queue_worker(self) -> None:
        ctx = self._require_ctx()
        while not ctx.stop_event.is_set():
            try:
                payload = await asyncio.wait_for(self._queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            try:
                await self._execute(payload)
            except Exception:
                logger.exception("自动化 %r 排队通知失败", self.name)
            finally:
                self._queue.task_done()
