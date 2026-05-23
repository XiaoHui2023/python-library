from __future__ import annotations

import asyncio
import logging
from concurrent.futures import Future as ConcurrentFuture
from typing import Any

from pydantic import Field, PrivateAttr

from automation.core.base import BaseAutomation, observer_bus
from automation.core.event import Event
from automation.core.info import CallInfo
from automation.core.registry_catalog import event_registry

logger = logging.getLogger(__name__)


class OnCallEvent(Event):
    """在基类事件之上按规格登记方法调用观测，匹配后触发 fire。"""

    on_calls: list[CallInfo] = Field(
        default_factory=list,
        description=(
            "与总线发派匹配的多条调用规格，逐项登记；"
            "某条方法名为空则该项不挂总线、仅可依赖其它触发路径"
        ),
    )

    _on_call_bridges_done: bool = PrivateAttr(default=False)

    async def on_activate(self) -> None:
        await super().on_activate()
        _register_on_call_bridges(self)

    async def on_inactive(self) -> None:
        self._on_call_bridges_done = False
        await super().on_inactive()


def _register_on_call_bridges(ev: OnCallEvent) -> None:
    """在总线上按本事件的调用规格登记，在匹配到调用后调度 fire。"""

    if ev._on_call_bridges_done:
        return

    from observer.context import ObserverContext

    for spec in ev.on_calls:
        if not spec.method_name:
            continue

        def on_observed_call(
            obs_ctx: ObserverContext, _spec: CallInfo = spec
        ) -> None:
            if obs_ctx.phase != "after":
                return
            if _spec.instance_type and obs_ctx.cls_name != _spec.instance_type:
                return
            inst = obs_ctx.instance
            if _spec.instance_name:
                if not isinstance(inst, BaseAutomation):
                    return
                if inst.instance_name != _spec.instance_name:
                    return
            else:
                if inst is None:
                    return
                if not isinstance(inst, BaseAutomation) or inst._ctx is not ev._ctx:
                    return
            loop = ev._ctx.main_loop
            if loop is None:
                logger.warning(
                    "事件 %s：主循环未就绪，无法在观测回调路径中向主循环调度 fire",
                    ev.instance_name,
                )
                return
            fut: ConcurrentFuture[Any] = asyncio.run_coroutine_threadsafe(
                ev.fire(dict(obs_ctx.kwargs)), loop
            )

            def _on_fire_done(done: ConcurrentFuture[Any]) -> None:
                exc = done.exception()
                if exc is not None:
                    logger.error(
                        "由观测触发的 fire 失败：%s",
                        exc,
                        exc_info=exc,
                    )

            fut.add_done_callback(_on_fire_done)

        filters: dict[str, Any] = {
            "phase": "after",
            "method_name": spec.method_name,
        }
        if spec.instance_type:
            filters["cls_name"] = spec.instance_type
        observer_bus.subscribe(on_observed_call, **filters)
        ev._ctx.register_observer_bridge_handler(on_observed_call)

    ev._on_call_bridges_done = True


OnCallEvent.registered_kind = "on_call"
event_registry.register("on_call", OnCallEvent)
