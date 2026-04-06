from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import inspect
from typing import Protocol


class Trackable(Protocol):
    @property
    def version(self) -> int: ...


class Collector:
    def __init__(self) -> None:
        self.deps: dict[int, Trackable] = {}

    def add(self, dep: Trackable) -> None:
        self.deps[id(dep)] = dep


class CircularDependencyError(RuntimeError):
    pass


_ACTIVE_COLLECTOR: ContextVar[Collector | None] = ContextVar(
    "_ACTIVE_COLLECTOR",
    default=None,
)

_COMPUTE_STACK: ContextVar[tuple[object, ...]] = ContextVar(
    "_COMPUTE_STACK",
    default=(),
)


def track(dep: Trackable) -> None:
    collector = _ACTIVE_COLLECTOR.get()
    if collector is not None:
        collector.add(dep)


def _format_expr(expr: object) -> str:
    file: str | None = None
    line: int | None = None
    code: str | None = None

    try:
        file = inspect.getsourcefile(expr) or inspect.getfile(expr)
    except Exception:
        pass

    try:
        lines, line = inspect.getsourcelines(expr)
        code = "".join(lines).strip()
    except Exception:
        pass

    location = "<unknown>" if file is None else f"{file}:{line}" if line is not None else file
    return f"{location} -> {code}" if code else location


def _build_cycle_message(cycle: tuple[object, ...]) -> str:
    lines = ["检测到循环依赖:"]
    for idx, item in enumerate(cycle, start=1):
        expr = getattr(item, "_expr", None)
        lines.append(f"{idx}. {_format_expr(expr)}")
    return "\n".join(lines)


@contextmanager
def compute_context(owner: object, collector: Collector):
    stack = _COMPUTE_STACK.get()
    if owner in stack:
        start = stack.index(owner)
        cycle = stack[start:] + (owner,)
        raise CircularDependencyError(_build_cycle_message(cycle))

    collector_token = _ACTIVE_COLLECTOR.set(collector)
    stack_token = _COMPUTE_STACK.set(stack + (owner,))
    try:
        yield
    finally:
        _COMPUTE_STACK.reset(stack_token)
        _ACTIVE_COLLECTOR.reset(collector_token)