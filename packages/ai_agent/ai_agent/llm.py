from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncIterator, Protocol

from ai_agent.context import RunContext


class StreamKind(str, Enum):
    """语言模型流式片段类型（库内统一）。"""

    TEXT = "text"
    REASONING = "reasoning"
    TOOL_CALL = "tool_call"
    DONE = "done"


@dataclass
class StreamChunk:
    """语言模型流式输出的一段；各适配器均映射为本类型。"""

    kind: StreamKind
    delta: str = ""
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None


class LLMClient(Protocol):
    """语言模型流式接口；库内由 OpenAILLM 实现。"""

    async def stream(
        self,
        context: RunContext,
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """按当前上下文流式请求语言模型。"""
