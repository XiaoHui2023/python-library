from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from openai import AsyncOpenAI

from ai_agent.context import (
    AgentContext,
    ChatMessage,
    RunContext,
    RunPhase,
    RunPhaseKind,
)
from ai_agent.listener import AgentListener, normalize_listeners
from ai_agent.llm import LLMClient
from ai_agent.llm_openai import OpenAILLM
from ai_agent.loop import ReactLoop
from ai_agent.rule import RuleSet
from ai_agent.tools import Tool, ToolRegistry


class Agent:
    """
    ReAct 运行入口：构造时组装 ``AgentContext`` 并驱动多步循环。

    系统提示由构造时的 ``rule_paths`` 指定文件读入；``run`` 只接收消息列表。
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        thinking_enabled: bool = False,
        tools: list[Tool] | ToolRegistry | None = None,
        rule_paths: list[str] | list[Path] | tuple[str, ...] | tuple[Path, ...] | None = None,
        max_steps: int = 20,
        listeners: AgentListener | Iterable[AgentListener] | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("api_key 不能为空")
        if not model.strip():
            raise ValueError("model 不能为空")
        if not base_url.strip():
            raise ValueError("base_url 不能为空")

        api_key = api_key.strip()
        model = model.strip()
        base_url = base_url.strip().rstrip("/")

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        llm: LLMClient = OpenAILLM(
            client,
            model=model,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_enabled=thinking_enabled,
        )
        if isinstance(tools, ToolRegistry):
            registry = tools
        else:
            registry = ToolRegistry(tools)
        self.context = AgentContext(
            llm=llm,
            tools=registry,
            max_steps=max_steps,
            listeners=normalize_listeners(listeners),
        )
        self._rules = RuleSet(rule_paths)

    @property
    def rules(self) -> RuleSet:
        """构造时绑定的规则集。"""
        return self._rules

    async def run(
        self,
        *,
        messages: list[ChatMessage],
    ) -> str:
        """
        运行一轮 ReAct 循环，返回最终回答文本。
        """
        return await self.run_with_system(
            system_prompt=self._rules.build_system_prompt(),
            messages=messages,
        )

    async def run_with_system(
        self,
        *,
        system_prompt: str,
        messages: list[ChatMessage],
        phase: RunPhase | None = None,
    ) -> str:
        """
        使用给定系统提示运行一轮（供会话层叠加计划步说明等）。

        Args:
            system_prompt: 本轮送入模型的完整系统提示
            messages: 用户与助手历史及本轮输入
        """
        run = RunContext(
            system_prompt=system_prompt,
            messages=list(messages),
            phase=phase or RunPhase(kind=RunPhaseKind.DIRECT),
        )
        if self.context.on_run_begin is not None:
            self.context.on_run_begin(run)
        try:
            loop = ReactLoop(self.context)
            async for updated in loop.run(run):
                run = updated
            return run.output
        finally:
            if self.context.on_run_end is not None:
                self.context.on_run_end(run)
