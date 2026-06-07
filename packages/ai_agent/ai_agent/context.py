from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from ai_agent.llm import LLMClient
    from ai_agent.listener import AgentListener
    from ai_agent.tools import ToolRegistry

MessageRole = Literal["system", "user", "assistant", "tool"]


class RunStatus(str, Enum):
    """一轮运行的整体状态。"""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    MAX_STEPS = "max_steps"


class RunPhaseKind(str, Enum):
    """监听回调所归属的运行阶段。"""

    DIRECT = "direct"


@dataclass(frozen=True)
class RunPhase:
    """单次 ReAct 所处的阶段。"""

    kind: RunPhaseKind = RunPhaseKind.DIRECT


@dataclass
class AgentContext:
    """
    Agent 运行环境：语言模型、工具表与 ReAct 步数上限。

    由 ``Agent`` 构造时创建；测试可替换 ``llm`` 等成员。
    """

    llm: LLMClient
    tools: ToolRegistry
    max_steps: int = 20
    listeners: list[AgentListener] = field(default_factory=list)
    on_run_begin: Callable[["RunContext"], None] | None = None
    on_run_end: Callable[["RunContext"], None] | None = None


@dataclass
class ChatMessage:
    """对话消息；用于历史记录与用户输入。"""

    role: MessageRole
    content: str
    name: str | None = None

    def to_api(self) -> dict[str, Any]:
        item: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name:
            item["name"] = self.name
        return item


@dataclass
class ToolInvocation:
    """按顺序记录的一次工具调用；运行中更新思考与回答。"""

    call_id: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    thinking: str = ""
    answer: str = ""
    ok: bool = True


@dataclass
class RunContext:
    """
    单轮运行的上下文：输入、按序工具调用与最终输出。

    运行上下文：系统提示与 messages；运行后读取 output 与 tool_invocations。
    """

    system_prompt: str = ""
    ephemeral_skill_context: str = ""
    messages: list[ChatMessage] = field(default_factory=list)
    tool_invocations: list[ToolInvocation] = field(default_factory=list)
    tool_turns: list[list[ToolInvocation]] = field(default_factory=list)
    thinking: str = ""
    output: str = ""
    status: RunStatus = RunStatus.RUNNING
    phase: RunPhase | None = None
    def api_messages(self) -> list[dict[str, Any]]:
        """组装送入语言模型的消息列表。"""
        out: list[dict[str, Any]] = []
        system = self._effective_system_prompt()
        if system:
            out.append({"role": "system", "content": system})
        out.extend(m.to_api() for m in self.messages)
        for turn in self.tool_turns:
            tool_calls: list[dict[str, Any]] = []
            for inv in turn:
                tool_calls.append(
                    {
                        "id": inv.call_id,
                        "type": "function",
                        "function": {
                            "name": inv.tool_name,
                            "arguments": json.dumps(inv.arguments, ensure_ascii=False),
                        },
                    }
                )
            assistant: dict[str, Any] = {
                "role": "assistant",
                "content": turn[0].thinking or None,
                "tool_calls": tool_calls,
            }
            out.append(assistant)
            for inv in turn:
                if inv.answer:
                    out.append(
                        {
                            "role": "tool",
                            "tool_call_id": inv.call_id,
                            "content": inv.answer,
                        }
                    )
        return out

    def _effective_system_prompt(self) -> str:
        base = self.system_prompt.strip()
        extra = self.ephemeral_skill_context.strip()
        if base and extra:
            return f"{base}\n\n{extra}"
        if extra:
            return extra
        return base