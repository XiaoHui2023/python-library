from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ai_agent.context import RunContext, ToolInvocation

if TYPE_CHECKING:
    from ai_agent.app.packet import RunOutputPacket
    from ai_agent.plan.models import Plan, PlanStep

ListenerCallback = Callable[..., Any] | Callable[..., Awaitable[Any]]


@dataclass
class AgentListener:
    """
    规划、逐步执行与应用交付的可选回调集合。

    流式思考与回答经 ``on_thinking_delta`` / ``on_output_delta`` 推送，
    调用方可读 ``RunContext.phase`` 区分规划、计划步与直连 ReAct。
    各钩子未设置时不调用；回调可为同步或 async 函数。
    """

    on_run_start: ListenerCallback | None = None
    on_run_end: ListenerCallback | None = None
    on_thinking_delta: ListenerCallback | None = None
    on_output_delta: ListenerCallback | None = None
    on_tool_start: ListenerCallback | None = None
    on_tool_end: ListenerCallback | None = None
    on_plan_start: ListenerCallback | None = None
    on_plan_ready: ListenerCallback | None = None
    on_plan_step_start: ListenerCallback | None = None
    on_plan_step_end: ListenerCallback | None = None
    on_app_run_end: ListenerCallback | None = None


def normalize_listeners(
    listeners: AgentListener | Iterable[AgentListener] | None,
) -> list[AgentListener]:
    """
    将单个或多个 listener 规范为列表。

    Args:
        listeners: 单个 ``AgentListener``、序列，或 ``None``

    Returns:
        供 ``AgentContext`` 使用的 listener 列表
    """
    if listeners is None:
        return []
    if isinstance(listeners, AgentListener):
        return [listeners]
    return list(listeners)


async def _invoke(callback: ListenerCallback, *args: Any) -> None:
    result = callback(*args)
    if inspect.isawaitable(result):
        await result


async def notify_run_start(listeners: Sequence[AgentListener], run: RunContext) -> None:
    for listener in listeners:
        if listener.on_run_start is not None:
            await _invoke(listener.on_run_start, run)


async def notify_run_end(listeners: Sequence[AgentListener], run: RunContext) -> None:
    for listener in listeners:
        if listener.on_run_end is not None:
            await _invoke(listener.on_run_end, run)


async def notify_thinking_delta(
    listeners: Sequence[AgentListener],
    delta: str,
    run: RunContext,
) -> None:
    if not delta:
        return
    for listener in listeners:
        if listener.on_thinking_delta is not None:
            await _invoke(listener.on_thinking_delta, delta, run)


async def notify_output_delta(
    listeners: Sequence[AgentListener],
    delta: str,
    run: RunContext,
) -> None:
    if not delta:
        return
    for listener in listeners:
        if listener.on_output_delta is not None:
            await _invoke(listener.on_output_delta, delta, run)


async def notify_tool_start(
    listeners: Sequence[AgentListener],
    invocation: ToolInvocation,
    run: RunContext,
) -> None:
    for listener in listeners:
        if listener.on_tool_start is not None:
            await _invoke(listener.on_tool_start, invocation, run)


async def notify_tool_end(
    listeners: Sequence[AgentListener],
    invocation: ToolInvocation,
    run: RunContext,
) -> None:
    for listener in listeners:
        if listener.on_tool_end is not None:
            await _invoke(listener.on_tool_end, invocation, run)


async def notify_plan_start(listeners: Sequence[AgentListener]) -> None:
    for listener in listeners:
        if listener.on_plan_start is not None:
            await _invoke(listener.on_plan_start)


async def notify_plan_ready(listeners: Sequence[AgentListener], plan: Plan) -> None:
    for listener in listeners:
        if listener.on_plan_ready is not None:
            await _invoke(listener.on_plan_ready, plan)


async def notify_plan_step_start(
    listeners: Sequence[AgentListener],
    *,
    step_index: int,
    step: PlanStep,
    plan: Plan,
) -> None:
    for listener in listeners:
        if listener.on_plan_step_start is not None:
            await _invoke(listener.on_plan_step_start, step_index, step, plan)


async def notify_plan_step_end(
    listeners: Sequence[AgentListener],
    *,
    step_index: int,
    step: PlanStep,
    plan: Plan,
    output: str,
    skipped: bool,
) -> None:
    for listener in listeners:
        if listener.on_plan_step_end is not None:
            await _invoke(
                listener.on_plan_step_end,
                step_index,
                step,
                plan,
                output,
                skipped,
            )


async def notify_app_run_end(
    listeners: Sequence[AgentListener],
    packet: RunOutputPacket,
) -> None:
    for listener in listeners:
        if listener.on_app_run_end is not None:
            await _invoke(listener.on_app_run_end, packet)
