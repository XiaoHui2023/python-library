from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any

from automation.core.entity import Entity
from automation.core.event import Event, EventContext
from automation.core.trigger import Trigger
from automation.core.renderer import Renderer
from automation.core.base import BaseAutomation
from automation.listener.base import BaseListener
from automation.listener.events import ListenerEvent, ObserverAfter

logger = logging.getLogger(__name__)


class Context:
    """各模块共享的运行时状态与表达式渲染入口。"""

    SECTIONS = ("entities", "events", "triggers")
    AUTOMATION_SECTIONS = ("entities", "events", "triggers")

    def __init__(self) -> None:
        self.entities: dict[str, Entity] = {}
        self.events: dict[str, Event] = {}
        self.triggers: dict[str, Trigger] = {}

        self.stop_event: asyncio.Event = asyncio.Event()
        self.listeners: list[BaseListener] = []
        self._on_state_changed: list = []
        self.main_loop: asyncio.AbstractEventLoop | None = None
        self._observer_bridge_handlers: list[Callable[..., Any]] = []
        self._observer_global_after_registered: bool = False
        self._event_fire_handlers: dict[
            str, list[Callable[[EventContext], Any]]
        ] = {}
        self._action_step_perf_start: float | None = None

    def mark_action_step_start(self) -> None:
        """记录当前一步动作耗时的起点（与 consume_action_step_elapsed 配对）。"""

        self._action_step_perf_start = time.perf_counter()

    def clear_action_step_timer(self) -> None:
        """丢弃当前一步动作计时起点（异常路径上避免遗留）。"""

        self._action_step_perf_start = None

    def consume_action_step_elapsed(self) -> float:
        """返回自 mark 以来经过的秒数并清除起点；若未 mark 则返回 0.0。

        Returns:
            秒数: 自上次 mark 起的经过时间；未 mark 时为 0.0。
        """

        t0 = self._action_step_perf_start
        self._action_step_perf_start = None
        if t0 is None:
            return 0.0
        return time.perf_counter() - t0

    def create_renderer(
        self, extra: dict[str, Any] | None = None
    ) -> Renderer:
        """基于当前分区快照构造根渲染器；子类可覆盖以换实现或包一层。

        Args:
            extra: 额外并入求值命名空间的键值；为 None 时不并入；同名键以这里为准。

        Returns:
            根渲染器实例
        """

        ns: dict[str, Any] = {
            "entities": self.entities,
            "events": self.events,
            "triggers": self.triggers,
            "context": self,
        }
        if extra is not None:
            ns.update(extra)
        return Renderer(ns)

    def emit(self, event: ListenerEvent) -> None:
        """将一条通知分发给已注册监听器。"""

        for listener in self.listeners:
            listener.handle(event)

    def section(self, name: str) -> Any:
        """按分区名返回对应字典视图。"""

        if name not in self.SECTIONS:
            raise KeyError(name)
        return getattr(self, name)

    def add_event_fire_handler(
        self,
        event_name: str,
        callback: Callable[[EventContext], Any],
    ) -> None:
        """注册在某事件通过条件并触发后要运行的回调（可与 listener 的 ``EventFired`` 并行）。"""

        self._event_fire_handlers.setdefault(event_name, []).append(callback)

    def remove_event_fire_handler(
        self,
        event_name: str,
        callback: Callable[[EventContext], Any],
    ) -> None:
        """移除由上面方法注册的回调。"""

        lst = self._event_fire_handlers.get(event_name)
        if not lst:
            return
        try:
            lst.remove(callback)
        except ValueError:
            pass
        if not lst:
            del self._event_fire_handlers[event_name]

    def get_event_fire_handlers(
        self, event_name: str
    ) -> list[Callable[[EventContext], Any]]:
        """返回指定事件当前已注册的触发回调（拷贝列表）。"""

        return list(self._event_fire_handlers.get(event_name, []))

    def register_observer_bridge_handler(self, fn: Callable[..., Any]) -> None:
        """登记将由 detach_observer_bridge 统一卸载的 observer 总线回调。"""

        self._observer_bridge_handlers.append(fn)

    def ensure_observer_global_after(self) -> None:
        """在总线上登记一次 after 阶段转发为监听的 After 通知（本上下文内幂等）。"""

        if self._observer_global_after_registered:
            return
        from automation.core.base import observer_bus
        from observer.context import ObserverContext

        def on_after(obs_ctx: ObserverContext) -> None:
            if obs_ctx.phase != "after":
                return
            inst = obs_ctx.instance
            if inst is None:
                return
            if not isinstance(inst, BaseAutomation) or inst._ctx is not self:
                return
            self.emit(ObserverAfter(obs_ctx))

        observer_bus.subscribe(on_after, phase="after")
        self.register_observer_bridge_handler(on_after)
        self._observer_global_after_registered = True

    def detach_observer_bridge(self) -> None:
        """卸载本上下文在 observer 总线上的全部桥接监听。"""

        from automation.core.base import observer_bus

        for fn in self._observer_bridge_handlers:
            observer_bus.unsubscribe(fn)
        self._observer_bridge_handlers.clear()
        self._observer_global_after_registered = False