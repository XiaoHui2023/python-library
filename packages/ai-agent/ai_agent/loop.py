from __future__ import annotations

from typing import AsyncIterator

from collections.abc import Sequence

from ai_agent.context import AgentContext, RunContext, RunStatus, ToolInvocation
from ai_agent.listener import (
    AgentListener,
    notify_output_delta,
    notify_run_end,
    notify_run_start,
    notify_thinking_delta,
    notify_tool_end,
    notify_tool_start,
)
from ai_agent.llm import StreamChunk, StreamKind
from ai_agent.react_tool_turn import deferred_tool_reply, should_defer_tool_in_batch


class ReactLoop:
    """多步 ReAct 运行；更新 RunContext 中的思考、工具实例与最终 output。"""

    def __init__(self, context: AgentContext) -> None:
        self._context = context

    async def run(self, run: RunContext) -> AsyncIterator[RunContext]:
        """
        驱动单轮上下文直至完成、失败或超步数；每有更新 yield 同一对象。
        """
        run.status = RunStatus.RUNNING
        run.thinking = ""
        run.output = ""
        await notify_run_start(self._context.listeners, run)
        yield run

        try:
            for _ in range(self._context.max_steps):
                run.thinking = ""
                pending_calls: list[ToolInvocation] = []
                api_tools = self._context.tools.api_tools() or None

                async for chunk in self._context.llm.stream(run, tools=api_tools):
                    self._apply_chunk(run, chunk, pending_calls)
                    await self._notify_chunk(self._context.listeners, chunk, run)
                    yield run
                    if chunk.kind == StreamKind.DONE:
                        break

                if pending_calls:
                    turn: list[ToolInvocation] = []
                    for inv in pending_calls:
                        run.tool_invocations.append(inv)
                        turn.append(inv)
                        yield run
                        await notify_tool_start(self._context.listeners, inv, run)
                        if should_defer_tool_in_batch(inv, pending_calls):
                            inv.answer = deferred_tool_reply()
                            inv.ok = True
                        else:
                            await self._context.tools.execute(inv)
                        await notify_tool_end(self._context.listeners, inv, run)
                        yield run
                    run.tool_turns.append(turn)
                    run.output = ""
                    continue
                if run.output:
                    run.status = RunStatus.COMPLETED
                    yield run
                    return

                if run.thinking and not run.output:
                    run.output = run.thinking
                    run.status = RunStatus.COMPLETED
                    yield run
                    return

            run.status = RunStatus.MAX_STEPS
            yield run

        except Exception:  # noqa: BLE001 — 运行边界
            run.status = RunStatus.FAILED
            yield run
            raise
        finally:
            await notify_run_end(self._context.listeners, run)

    async def _notify_chunk(
        self,
        listeners: Sequence[AgentListener],
        chunk: StreamChunk,
        run: RunContext,
    ) -> None:
        if not chunk.delta:
            return
        if chunk.kind == StreamKind.REASONING:
            await notify_thinking_delta(listeners, chunk.delta, run)
        elif chunk.kind == StreamKind.TEXT:
            await notify_output_delta(listeners, chunk.delta, run)

    def _apply_chunk(
        self,
        run: RunContext,
        chunk: StreamChunk,
        pending_calls: list[ToolInvocation],
    ) -> None:
        if chunk.kind == StreamKind.REASONING:
            if chunk.delta:
                run.thinking += chunk.delta
                if pending_calls:
                    pending_calls[-1].thinking += chunk.delta
        elif chunk.kind == StreamKind.TEXT:
            if chunk.delta:
                run.output += chunk.delta
        elif chunk.kind == StreamKind.TOOL_CALL:
            if chunk.tool_call_id and chunk.tool_name is not None:
                inv = ToolInvocation(
                    call_id=chunk.tool_call_id,
                    tool_name=chunk.tool_name,
                    arguments=dict(chunk.tool_arguments or {}),
                    thinking=run.thinking,
                )
                pending_calls.append(inv)
                run.thinking = ""
