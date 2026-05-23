from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from automation.listener.base import BaseListener
from automation.listener.events import Loaded, Started, Stopped
from automation.runtime.bootstrap import load_script, reload_automation, teardown_automation
from automation.runtime.global_state import (
    RunState,
    add_listener,
    get_context,
    get_main_loop,
    get_run_state,
    set_listeners,
    set_main_loop,
    set_run_state,
)

logger = logging.getLogger(__name__)


def context():
    """进程内唯一的自动化运行时上下文。"""

    return get_context()


def entities():
    return get_context().entities


def events():
    return get_context().events


def triggers():
    return get_context().triggers


def section(name: str):
    return get_context().section(name)


async def load_script_file(path: str | Path) -> None:
    """执行自动化脚本并激活其中注册的实体/事件/触发器。"""

    await load_script(path)
    get_context().emit(Loaded(get_context()))


async def start() -> None:
    if get_run_state() == RunState.RUNNING:
        return
    set_run_state(RunState.RUNNING)
    ctx = get_context()
    ctx.stop_event.clear()
    set_main_loop(asyncio.get_running_loop())
    ctx.main_loop = get_main_loop()
    for section_name in ctx.AUTOMATION_SECTIONS:
        for obj in ctx.section(section_name).values():
            await obj.run_phase()
    ctx.emit(Started())


async def run() -> None:
    await start()
    await get_context().stop_event.wait()


async def stop() -> None:
    if get_run_state() != RunState.RUNNING:
        return
    set_run_state(RunState.STOPPED)
    ctx = get_context()
    ctx.main_loop = None
    set_main_loop(None)
    for section_name in reversed(ctx.AUTOMATION_SECTIONS):
        for obj in ctx.section(section_name).values():
            await obj.run_phase(closing=True)
    ctx.stop_event.set()
    ctx.emit(Stopped())


def configure_listeners(
    listeners: list[BaseListener] | BaseListener | None = None,
) -> None:
    """登记监听器；须在 load_script 或 reload_automation 之前调用。"""

    if listeners is None:
        set_listeners([])
        return
    merged = (
        [listeners] if isinstance(listeners, BaseListener) else list(listeners)
    )
    set_listeners(merged)


__all__ = [
    "context",
    "entities",
    "events",
    "triggers",
    "section",
    "configure_listeners",
    "add_listener",
    "load_script_file",
    "reload_automation",
    "start",
    "run",
    "stop",
]
