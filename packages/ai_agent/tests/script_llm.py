from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator

from ai_agent.context import RunContext
from ai_agent.llm import StreamChunk, StreamKind


@dataclass
class ScriptLLM:
    """测试用脚本化流，不访问网络。"""

    _scripts: list[list[StreamChunk]]

    async def stream(
        self,
        context: RunContext,
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        del context, tools
        if not self._scripts:
            yield StreamChunk(kind=StreamKind.TEXT, delta="(empty script)")
            yield StreamChunk(kind=StreamKind.DONE)
            return
        for chunk in self._scripts.pop(0):
            yield chunk
        yield StreamChunk(kind=StreamKind.DONE)
