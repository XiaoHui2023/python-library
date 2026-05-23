from __future__ import annotations

import asyncio
from enum import StrEnum

from automation.listener.base import BaseListener
from automation.runtime.context import Context

_context = Context()
_listeners: list[BaseListener] = []


class RunState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"


_run_state = RunState.IDLE
_main_loop: asyncio.AbstractEventLoop | None = None


def get_context() -> Context:
    """返回进程内唯一的自动化运行时上下文。"""

    return _context


def get_listeners() -> list[BaseListener]:
    return _listeners


def set_listeners(items: list[BaseListener]) -> None:
    global _listeners
    _listeners = list(items)
    _context.listeners = _listeners


def add_listener(listener: BaseListener | list[BaseListener]) -> None:
    if isinstance(listener, list):
        _listeners.extend(listener)
    else:
        _listeners.append(listener)
    _context.listeners = _listeners


def get_run_state() -> RunState:
    return _run_state


def set_run_state(state: RunState) -> None:
    global _run_state
    _run_state = state


def get_main_loop() -> asyncio.AbstractEventLoop | None:
    return _main_loop


def set_main_loop(loop: asyncio.AbstractEventLoop | None) -> None:
    global _main_loop
    _main_loop = loop
