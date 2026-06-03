from __future__ import annotations

from collections.abc import Sequence

from ai_agent.context import ChatMessage, RunContext, RunPhase, RunPhaseKind
from ai_agent.listener import (
    AgentListener,
    notify_output_delta,
    notify_thinking_delta,
)
from ai_agent.llm import LLMClient, StreamKind


async def complete_text(
    llm: LLMClient,
    *,
    system_prompt: str,
    user_content: str,
    history: list[ChatMessage] | None = None,
    listeners: Sequence[AgentListener] | None = None,
    phase: RunPhase | None = None,
    parse_from_answer_text_only: bool = False,
) -> str:
    """
    无工具单次补全，收集流式文本。

    Args:
        llm: 与执行 Agent 共用的语言模型客户端
        system_prompt: 系统提示
        user_content: 本轮用户内容
        history: 规划前对话历史（不含本轮 user）
        parse_from_answer_text_only: 为 True 时返回值仅含 TEXT 流（思考流仍通知 listener，
            但不参与返回，供规划 JSON 解析，避免思考草稿中的 JSON 覆盖正式回答）

    Returns:
        模型完整文本
    """
    messages = list(history or [])
    messages.append(ChatMessage(role="user", content=user_content))
    planning_phase = phase or RunPhase(kind=RunPhaseKind.PLANNING)
    run = RunContext(
        system_prompt=system_prompt,
        messages=messages,
        phase=planning_phase,
    )
    active_listeners = list(listeners or [])
    all_parts: list[str] = []
    answer_parts: list[str] = []
    async for chunk in llm.stream(run, tools=None):
        if chunk.kind == StreamKind.REASONING and chunk.delta:
            if not parse_from_answer_text_only:
                all_parts.append(chunk.delta)
            await notify_thinking_delta(active_listeners, chunk.delta, run)
        elif chunk.kind == StreamKind.TEXT and chunk.delta:
            all_parts.append(chunk.delta)
            answer_parts.append(chunk.delta)
            await notify_output_delta(active_listeners, chunk.delta, run)
    if parse_from_answer_text_only:
        text = "".join(answer_parts).strip()
    else:
        text = "".join(all_parts).strip()
    if not text and run.output:
        return run.output.strip()
    return text
